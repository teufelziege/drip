import json, subprocess, tempfile, unittest, os, time
from pathlib import Path
from datetime import datetime, timezone, timedelta
BINARY = str(Path(__file__).resolve().parents[1] / 'build/drip')
class CounterTests(unittest.TestCase):
    def test_incremental_counting(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); sessions = root/'sessions'; sessions.mkdir()
            log = sessions/'old-conversation.jsonl'
            now = datetime.now(timezone.utc)
            def event(id, trigger='user', time=now):
                return json.dumps({'type':'event_msg','timestamp':time.isoformat(timespec='milliseconds'), 'payload':{'type':'task_started','turn_id':id,'turn_attribution':{'turn_trigger':trigger,'initiating_agent_path':None}}})+'\n'
            log.write_text(event('one')+event('one')+event('review','guardian_review')+event('yesterday',time=now-timedelta(days=1)))
            cmd = [BINARY,'--sessions',str(sessions),'--state',str(root/'state.json')]
            def run(*args): return json.loads(subprocess.check_output(cmd+list(args)))
            self.assertEqual(run()['prompts'],1)
            self.assertEqual(run()['running'],2)
            with log.open('a') as f:
                for id in ('one','yesterday'):
                    f.write(json.dumps({'type':'event_msg','payload':{'type':'task_complete','turn_id':id}})+'\n')
            self.assertEqual(run()['running'],0)
            self.assertEqual(run()['prompts'],1)
            with log.open('a') as f: f.write(event('two').rstrip('\n'))
            self.assertEqual(run()['prompts'],1)
            with log.open('a') as f: f.write('\n')
            self.assertEqual(run()['prompts'],2)
            self.assertEqual(run()['running'],1)
            with log.open('a') as f: f.write(json.dumps({'type':'event_msg','payload':{'type':'turn_aborted','turn_id':'two'}})+'\n')
            self.assertEqual(run()['running'],0)
            self.assertAlmostEqual(run()['ml'],0.64)
            self.assertAlmostEqual(run('--rate','1.5')['ml'],3)
            self.assertEqual(run()['rate'],1.5)
            invalid=subprocess.run(cmd+['--rate','nan'],capture_output=True)
            self.assertNotEqual(invalid.returncode,0)
            state=root/'state.json'; state.write_text('broken')
            self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            self.assertEqual(state.read_text(),'broken')
    def test_replaced_log_and_retention(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); sessions = root/'sessions'; sessions.mkdir()
            log = sessions/'log.jsonl'
            state = root/'state.json'
            cmd = [BINARY, '--sessions', str(sessions), '--state', str(state)]
            def event(identifier, when):
                return json.dumps({'type':'event_msg','timestamp':when.isoformat(timespec='milliseconds'),
                    'payload':{'type':'task_started','turn_id':identifier,
                    'turn_attribution':{'turn_trigger':'user'}}})+'\n'
            now = datetime.now(timezone.utc)
            log.write_text(event('first', now))
            def run(): return json.loads(subprocess.check_output(cmd))
            self.assertEqual(run()['prompts'], 1)
            replacement = sessions/'replacement'
            replacement.write_text(event('second', now) + ' '*200 + '\n')
            replacement.replace(log)
            self.assertEqual(run()['prompts'], 2)
            saved = json.loads(state.read_text())
            self.assertEqual(saved['activity_version'], 2)
            self.assertIn('files', saved)
            self.assertNotIn('first', saved['active'])
            self.assertEqual(run()['prompts'], 2)

    def test_stale_activity_is_per_turn(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); sessions=root/'sessions'; sessions.mkdir()
            log=sessions/'log.jsonl'
            now=datetime.now(timezone.utc)
            log.write_text(json.dumps({'type':'event_msg','timestamp':now.isoformat(),
                'payload':{'type':'task_started','turn_id':'one',
                'turn_attribution':{'turn_trigger':'user'}}})+'\n')
            state=root/'state.json'
            cmd=[BINARY,'--sessions',str(sessions),'--state',str(state)]
            self.assertEqual(json.loads(subprocess.check_output(cmd))['running'],1)
            data=json.loads(state.read_text())
            for entry in data['active'].values(): entry['seen']=0
            state.write_text(json.dumps(data))
            log.write_text(log.read_text()+'{}\n')
            self.assertEqual(json.loads(subprocess.check_output(cmd))['running'],0)

    def test_parallel_sessions_and_activity_heartbeat(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); sessions=root/'sessions'; sessions.mkdir()
            now=datetime.now(timezone.utc)
            def record(kind, identifier, trigger='user'):
                return json.dumps({'type':'event_msg','timestamp':now.isoformat(),
                    'payload':{'type':kind,'turn_id':identifier,
                    'turn_attribution':{'turn_trigger':trigger}}})+'\\n'
            a=sessions/'a.jsonl'; b=sessions/'b.jsonl'
            a.write_text(record('task_started','shared'))
            b.write_text(record('task_started','shared'))
            state=root/'state.json'
            cmd=[BINARY,'--sessions',str(sessions),'--state',str(state)]
            def run(): return json.loads(subprocess.check_output(cmd))
            self.assertEqual(run()['prompts'],2)
            self.assertEqual(run()['running'],2)
            with a.open('a') as out: out.write(record('task_complete','shared'))
            self.assertEqual(run()['running'],1)
            data=json.loads(state.read_text())
            for entry in data['active'].values(): entry['seen']=0
            state.write_text(json.dumps(data))
            with b.open('a') as out: out.write(record('agent_message','shared'))
            self.assertEqual(run()['running'],1)
            self.assertEqual(run()['prompts'],2)

    def test_append_short_log_does_not_replay_active_turn(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); sessions=root/'sessions'; sessions.mkdir()
            log=sessions/'short.jsonl'
            now=datetime.now(timezone.utc).isoformat()
            def record(kind, identifier):
                return json.dumps({'type':'event_msg','timestamp':now,
                    'payload':{'type':kind,'turn_id':identifier,
                    'turn_attribution':{'turn_trigger':'user'}}})+'\\n'
            log.write_text(record('task_started','first'))
            state=root/'state.json'
            cmd=[BINARY,'--sessions',str(sessions),'--state',str(state)]
            def run(): return json.loads(subprocess.check_output(cmd))
            self.assertEqual(run()['running'],1)
            with log.open('a') as out: out.write(record('task_complete','first'))
            self.assertEqual(run()['running'],0)
            with log.open('a') as out: out.write(record('task_started','second'))
            self.assertEqual(run()['running'],1)
            self.assertEqual(run()['prompts'],2)

    def test_invalid_state_schema_and_rate_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); sessions=root/'sessions'; sessions.mkdir()
            state=root/'state.json'
            cmd=[BINARY,'--sessions',str(sessions),'--state',str(state)]
            for invalid in ({'offsets':[]},{'events':[]},{'active':[]},
                            {'files':[]},{'ml_per_prompt':-1},
                            {'ml_per_prompt':'wrong'}):
                serialized=json.dumps(invalid)
                state.write_text(serialized)
                self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
                self.assertEqual(state.read_text(),serialized)

    def test_day_boundary_and_retention(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); sessions=root/'sessions'; sessions.mkdir()
            log=sessions/'history.jsonl'
            now=datetime.now().astimezone()
            def event(identifier, moment):
                return json.dumps({'type':'event_msg','timestamp':moment.isoformat(),
                    'payload':{'type':'task_started','turn_id':identifier,
                    'turn_attribution':{'turn_trigger':'user'}}})+'\\n'
            log.write_text(event('today',now)+event('yesterday',now-timedelta(days=1))
                           +event('old',now-timedelta(days=10)))
            state=root/'state.json'
            cmd=[BINARY,'--sessions',str(sessions),'--state',str(state)]
            self.assertEqual(json.loads(subprocess.check_output(cmd))['prompts'],1)
            data=json.loads(state.read_text())
            self.assertEqual(len(data['events']),2)

if __name__=='__main__': unittest.main()
