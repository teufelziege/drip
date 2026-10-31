import json, subprocess, tempfile, unittest
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
if __name__=='__main__': unittest.main()
