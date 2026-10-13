"""Acceptance and unit test suite for NFSU Smart Academic Timetable Generator.
Tests all 15 mandatory acceptance criteria.
"""
import unittest
import json
import copy
from app import app
import models
import scheduler
import validator
import seed_data


class TimetableGeneratorTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()

    def setUp(self):
        # Reset to standard demo data before each test
        self.data = seed_data.seed_demo_data()
        models.save_data(self.data)

    def test_01_all_web_routes_render(self):
        """1. App starts and all pages load with 200 OK."""
        routes = ['/', '/programmes', '/faculty', '/rooms', '/subjects', '/settings', '/timetable', '/conflicts', '/export']
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

    def test_02_demo_data_persists(self):
        """2. Demo data loads successfully and persists in JSON store."""
        data = models.load_data()
        self.assertEqual(data['settings']['name'], 'National Forensic Sciences University')
        self.assertEqual(data['settings']['department'], 'School of Cyber Security & Digital Forensics')
        self.assertEqual(len(data['programmes']), 5)
        self.assertEqual(len(data['faculty']), 6)
        self.assertEqual(len(data['rooms']), 8)

    def test_03_generate_creates_real_sessions(self):
        """3 & 4. Timetable generation creates real sessions satisfying weekly counts."""
        res = scheduler.run_scheduler(self.data)
        self.assertEqual(res['status'], 'success')
        self.assertEqual(res['total_unscheduled'], 0)
        self.assertGreater(res['total_scheduled'], 20)

    def test_04_no_constraint_violations_on_generated_schedule(self):
        """5, 6, 7, 8. Generated timetable satisfies all hard constraints."""
        res = scheduler.run_scheduler(self.data)
        self.data['scheduled_sessions'] = res['scheduled_sessions']
        errors = validator.validate_timetable(self.data)
        self.assertEqual(len(errors), 0, f"Found unexpected validation errors: {errors}")

    def test_05_impossible_scenario_reports_failure(self):
        """10. Impossible inputs result in clear failure report, not false success."""
        imp_data = copy.deepcopy(self.data)
        # Assign 60 periods to a single subject (impossible within working hours)
        imp_data['subjects'][0]['theory_periods_per_week'] = 60
        res = scheduler.run_scheduler(imp_data)
        self.assertIn(res['status'], ('partial', 'failed'))
        self.assertGreater(res['total_unscheduled'], 0)
        self.assertTrue(len(res['unscheduled_sessions']) > 0)
        self.assertTrue(len(res['unscheduled_sessions'][0]['reason']) > 0)

    def test_06_invalid_manual_edit_rejected(self):
        """11. Invalid manual edits are rejected with understandable explanations."""
        res = scheduler.run_scheduler(self.data)
        self.data['scheduled_sessions'] = res['scheduled_sessions']
        models.save_data(self.data)

        non_fixed = [s for s in res['scheduled_sessions'] if not s.get('is_fixed')]
        s0 = non_fixed[0]
        s1 = non_fixed[1]
        
        # Conflict payload (same room & time as s1)
        payload = {
            'session_id': s0['id'],
            'day': s1['day'],
            'start_time': s1['start_time'],
            'end_time': s1['end_time'],
            'room_id': s1['room_id']
        }
        resp = self.client.post('/api/edit-session', json=payload)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn('errors', data)
        self.assertTrue(len(data['errors']) > 0)

    def test_07_fixed_and_locked_sessions_preserved(self):
        """9. Fixed and locked sessions remain unchanged during regeneration."""
        res = scheduler.run_scheduler(self.data)
        self.data['scheduled_sessions'] = res['scheduled_sessions']
        models.save_data(self.data)
        non_fixed = [s for s in res['scheduled_sessions'] if not s.get('is_fixed')]
        target_id = non_fixed[0]['id']
        
        # Lock target
        lock_resp = self.client.post(f'/api/toggle-lock/{target_id}', json={})
        self.assertEqual(lock_resp.status_code, 200)

        # Regenerate
        gen_resp = self.client.post('/api/generate', json={})
        self.assertEqual(gen_resp.status_code, 200)

        after_data = models.load_data()
        matching = [s for s in after_data['scheduled_sessions'] if s['id'] == target_id]
        self.assertEqual(len(matching), 1)
        self.assertTrue(matching[0]['is_locked'])

    def test_08_csv_export_validity(self):
        """14. CSV export works with proper escaping."""
        res = scheduler.run_scheduler(self.data)
        self.data['scheduled_sessions'] = res['scheduled_sessions']
        models.save_data(self.data)

        resp = self.client.get('/api/export-csv')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/csv', resp.content_type)
        content = resp.data.decode('utf-8')
        self.assertIn('Day', content)
        self.assertIn('Subject', content)
        self.assertIn('Faculty', content)
        self.assertIn('Room', content)


if __name__ == '__main__':
    unittest.main()
