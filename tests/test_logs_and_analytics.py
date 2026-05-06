import unittest
from unittest.mock import AsyncMock, patch

from api import analytics, logs
from models.log_entry import LogEntry


class LogsAndAnalyticsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        logs.logs_db.clear()

    def tearDown(self):
        logs.logs_db.clear()

    async def test_add_log_replaces_raw_resource_ids_in_message(self):
        entry = LogEntry(
            level='INFO',
            event_type='mob_kill',
            message='mob_kill: minecraft:zombie рядом с minecraft:oak_log',
            event_data={'entity_id': 'minecraft:zombie'},
        )

        await logs.add_log(entry)

        self.assertEqual(len(logs.logs_db), 1)
        self.assertIn('зомби', logs.logs_db[0].message.lower())
        self.assertNotIn('minecraft:zombie', logs.logs_db[0].message)
        self.assertIn('дубовое бревно', logs.logs_db[0].message.lower())

    async def test_session_summary_replaces_raw_resource_ids_in_analysis_markdown(self):
        logs.logs_db.append(
            LogEntry(
                level='INFO',
                event_type='death',
                message='death: minecraft:zombie атаковал у minecraft:oak_log',
            )
        )

        with (
            patch.object(analytics.groq_client, 'is_available', return_value=True),
            patch.object(
                analytics.groq_client,
                'generate_analytics_async',
                new=AsyncMock(return_value='## Итог\n- Игрок столкнулся с minecraft:zombie возле minecraft:oak_log.'),
            ),
        ):
            result = await analytics.get_session_summary()

        self.assertEqual(result['status'], 'success')
        self.assertIn('зомби', result['analysis_markdown'].lower())
        self.assertIn('дубовое бревно', result['analysis_markdown'].lower())
        self.assertNotIn('minecraft:zombie', result['analysis_markdown'])
        self.assertIn('<h2>Итог</h2>', result['analysis_html'])
        self.assertIn('<li>Игрок столкнулся с зомби возле дубовое бревно.</li>', result['analysis_html'])
