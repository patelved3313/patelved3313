from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest
from update_activity import parse_calendar, refresh, render_activity, summarize


class ActivityTests(unittest.TestCase):
    def test_streak_crosses_year_boundary_and_allows_today_to_be_empty(self):
        today = date(2027, 1, 2)
        days = {date(2026, 12, 30): 1, date(2026, 12, 31): 3,
                date(2027, 1, 1): 2, today: 0}
        current, longest, recent = summarize(days, today)
        self.assertEqual((current, longest), (3, 3))
        self.assertEqual(len(recent), 31)
        self.assertEqual(sum(c for _, c in recent), 6)

    def test_a_missed_yesterday_resets_current_but_not_longest(self):
        today = date(2026, 9, 15)
        days = {today - timedelta(days=3): 2, today - timedelta(days=2): 1,
                today - timedelta(days=1): 0, today: 0}
        self.assertEqual(summarize(days, today)[:2], (0, 2))
        days[today] = 1
        self.assertEqual(summarize(days, today)[:2], (1, 2))

    def test_future_dates_do_not_extend_streak_or_graph(self):
        today = date(2026, 9, 15)
        days = {today: 1, today + timedelta(days=1): 100}
        current, longest, recent = summarize(days, today)
        self.assertEqual((current, longest), (1, 1))
        self.assertEqual(sum(c for _, c in recent), 1)

    def test_calendar_joins_dates_and_counts_by_id_not_display_order(self):
        html = '''<td data-date="2026-01-02" id="b"></td>
        <td data-date="2026-01-01" id="a"></td>
        <tool-tip for="a">1,234 contributions on January 1st.</tool-tip>
        <tool-tip for="b">No contributions\non January 2nd.</tool-tip>'''
        self.assertEqual(parse_calendar(html, date(2026, 1, 1), date(2026, 1, 2)),
                         {date(2026, 1, 1): 1234, date(2026, 1, 2): 0})

    def test_missing_day_and_unrecognized_count_are_rejected(self):
        for html in ['<html>Service unavailable</html>',
                     '<td data-date="2026-01-01" id="a"></td><tool-tip for="a">Unknown</tool-tip>',
                     '<td data-date="2026-01-01" id="a"></td><tool-tip for="a">0 contributions</tool-tip>']:
            with self.subTest(html=html), self.assertRaises(ValueError):
                parse_calendar(html, date(2026, 1, 1), date(2026, 1, 2))

    def test_duplicate_date_is_rejected(self):
        html = '''<td data-date="2026-01-01" id="a"></td>
        <td data-date="2026-01-01" id="b"></td>
        <tool-tip for="a">1 contribution</tool-tip><tool-tip for="b">2 contributions</tool-tip>'''
        with self.assertRaises(ValueError):
            parse_calendar(html, date(2026, 1, 1), date(2026, 1, 1))

    def test_failed_or_partial_refresh_keeps_both_previous_assets(self):
        def failed(year, today):
            raise OSError('GitHub unavailable')
        def incomplete(year, today):
            return {today: 1}
        with tempfile.TemporaryDirectory() as directory:
            assets = Path(directory)
            for name in ('activity.svg', 'activity-mobile.svg'):
                (assets / name).write_text('last valid snapshot')
            for fetcher in (failed, incomplete):
                with self.subTest(fetcher=fetcher), self.assertRaises((OSError, ValueError)):
                    refresh(date(2026, 9, 15), assets=assets, fetcher=fetcher)
                self.assertTrue(all(p.read_text() == 'last valid snapshot' for p in assets.iterdir()))

    def test_zero_activity_is_truthful_and_both_sizes_are_valid_svg(self):
        import xml.etree.ElementTree as ET
        today = date(2026, 9, 15)
        for mobile in (False, True):
            svg = render_activity({today: 0}, today, mobile)
            root = ET.fromstring(svg)
            description = root.find('{http://www.w3.org/2000/svg}desc').text
            self.assertIn('Current daily streak: 0 days', description)
            line = root.find('.//{http://www.w3.org/2000/svg}polyline')
            self.assertEqual({float(p.split(',')[1]) for p in line.get('points').split()}, {277.0})


if __name__ == '__main__':
    unittest.main()
