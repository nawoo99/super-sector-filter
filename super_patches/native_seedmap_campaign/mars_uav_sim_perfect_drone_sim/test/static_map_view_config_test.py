#!/usr/bin/env python3
"""Offline config/launch checks; no ROS node, publisher, simulator or RViz starts."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

import yaml
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.utilities import perform_substitutions
from launch_ros.actions import Node


PACKAGE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'static_map_view_launch', PACKAGE / 'launch/static_map_view.launch.py')
VIEW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VIEW)


def static_topics(value):
    if isinstance(value, dict):
        if value.get('Value') == '/global_pc':
            yield value
        for child in value.values():
            yield from static_topics(child)
    elif isinstance(value, list):
        for child in value:
            yield from static_topics(child)


class StaticMapViewConfigTest(unittest.TestCase):
    def test_only_static_map_qos_differs(self):
        for view in VIEW.VIEWS:
            with self.subTest(view=view):
                old_text = (PACKAGE / 'rviz2' / (view + '.rviz')).read_text()
                new_text = (PACKAGE / 'rviz2' / (view + '_durable.rviz')).read_text()
                old = yaml.safe_load(old_text)
                new = yaml.safe_load(new_text)
                old_topics = list(static_topics(old))
                new_topics = list(static_topics(new))
                self.assertEqual(len(old_topics), 1)
                self.assertEqual(len(new_topics), 1)
                self.assertEqual(old_topics[0], {
                    'Depth': 3, 'Durability Policy': 'Volatile',
                    'History Policy': 'Keep Last', 'Reliability Policy': 'Best Effort',
                    'Value': '/global_pc'})
                self.assertEqual(new_topics[0], {
                    'Depth': 1, 'Durability Policy': 'Transient Local',
                    'History Policy': 'Keep Last', 'Reliability Policy': 'Reliable',
                    'Value': '/global_pc'})
                expected = copy.deepcopy(old)
                next(static_topics(expected)).update(new_topics[0])
                self.assertEqual(new, expected)
                old_block = ('Depth: 3\n            Durability Policy: Volatile\n'
                             '            History Policy: Keep Last\n'
                             '            Reliability Policy: Best Effort\n'
                             '            Value: /global_pc')
                new_block = ('Depth: 1\n            Durability Policy: Transient Local\n'
                             '            History Policy: Keep Last\n'
                             '            Reliability Policy: Reliable\n'
                             '            Value: /global_pc')
                self.assertEqual(old_text.count(old_block), 1)
                self.assertEqual(new_text, old_text.replace(old_block, new_block))
                self.assertEqual(new['Visualization Manager']['Global Options']['Fixed Frame'], 'world')

    def test_explicit_selection_for_every_view(self):
        for view in VIEW.VIEWS:
            self.assertEqual(VIEW.select_rviz_filename(view, 'false'), view + '.rviz')
            self.assertEqual(VIEW.select_rviz_filename(view, 'true'), view + '_durable.rviz')

    def test_invalid_inputs_rejected(self):
        for value in ('', '1', '0', 'True', 'False', 'yes', ' true'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                VIEW.select_rviz_filename('watch_sector', value)
        for view in ('', '../watch_sector', 'watch_sector_durable', 'other'):
            with self.subTest(view=view), self.assertRaises(ValueError):
                VIEW.select_rviz_filename(view, 'true')

    def test_default_is_legacy_and_actions_are_reader_only(self):
        description = VIEW.generate_launch_description()
        arguments = {action.name: action for action in description.entities
                     if isinstance(action, DeclareLaunchArgument)}
        context = LaunchContext()
        self.assertEqual(perform_substitutions(context, arguments['durable'].default_value), 'false')
        self.assertEqual(perform_substitutions(context, arguments['view'].default_value), 'watch_sector')
        for durable in ('false', 'true'):
            context.launch_configurations.update(view='watch_sector', durable=durable)
            environment_before = dict(context.environment)
            with patch.object(VIEW, 'get_package_share_directory', return_value=str(PACKAGE)):
                actions = VIEW.launch_view(context)
            self.assertEqual(len(actions), 2)
            self.assertIsInstance(actions[0], LogInfo)
            self.assertIsInstance(actions[1], Node)
            self.assertEqual(actions[1].node_package, 'rviz2')
            self.assertEqual(context.environment, environment_before)

    def test_missing_installed_config_fails(self):
        context = LaunchContext()
        context.launch_configurations.update(view='watch_sector', durable='true')
        with patch.object(VIEW, 'get_package_share_directory', return_value='/nonexistent/static-map-test'):
            with self.assertRaises(RuntimeError):
                VIEW.launch_view(context)


if __name__ == '__main__':
    unittest.main(verbosity=2)
