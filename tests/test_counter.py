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

if __name__=='__main__': unittest.main()
