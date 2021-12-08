#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from unittest import TestCase
from unittest.mock import Mock, patch

from LabExT.Movement.MoverNew import MoverNew, MoverError, assert_connected_stages
from LabExT.Movement.Stage import Stage


class MoverBaseCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expermiment_manager = Mock()
        cls.connected_stage = Mock(connected=True)
        cls.disconnected_stage = Mock(connected=False)
        with patch.object(Stage, 'discovery', return_value=[cls.connected_stage, cls.disconnected_stage]):
            cls.mover = MoverNew(cls.expermiment_manager)

    @classmethod
    def tearDownClass(cls) -> None:
        del cls.expermiment_manager

    def tearDown(self) -> None:
        self.connected_stage.reset_mock()
        self.disconnected_stage.reset_mock()

    #
    #   Testing Decorators
    #

    def test_assert_connected_stages_calls_function(self):
        func = Mock()
        func.__name__ = 'Dummy Function'
        assert_connected_stages(func)(self.mover)
        func.assert_called_once()

    #
    #   Testing Mover Properties
    #

    def test_stage_filtering(self):
        self.assertListEqual(
            self.mover.connected_stages, [
                self.connected_stage])
        self.assertListEqual(
            self.mover.disconnected_stages, [
                self.disconnected_stage])

    def test_all_connected(self):
        self.assertFalse(self.mover.all_connected)

    def test_all_disconnected(self):
        self.assertFalse(self.mover.all_disconnected)

    #
    #   Testing Stage Connection
    #

    def test_connect_to_all(self):
        self.mover.connect()

        self.connected_stage.connect.assert_called_once()
        self.disconnected_stage.connect.assert_called_once()

    def test_connect_to_stage_by_index(self):
        self.mover.connect_stage_by_index(1)

        self.connected_stage.connect.assert_not_called()
        self.disconnected_stage.connect.assert_called_once()

    def test_disconnect_to_all(self):
        self.mover.disconnect()

        self.connected_stage.disconnect.assert_called_once()
        self.disconnected_stage.disconnect.assert_not_called()

    def test_connect_to_stage_by_index(self):
        self.mover.disconnect_stage_by_index(0)

        self.connected_stage.disconnect.assert_called_once()
        self.disconnected_stage.disconnect.assert_not_called()

    #
    #   Testing Mover Settings
    #

    def test_speed_xy_setter(self):
        new_speed = 123.45
        self.mover.speed_xy = new_speed

        self.connected_stage.set_speed_xy.assert_called_once_with(new_speed)
        self.disconnected_stage.set_speed_xy.assert_not_called()
        self.assertEqual(self.mover._speed_xy, new_speed)

    def test_speed_z_setter(self):
        new_speed = 123.45
        self.mover.speed_z = new_speed

        self.connected_stage.set_speed_z.assert_called_once_with(new_speed)
        self.disconnected_stage.set_speed_z.assert_not_called()
        self.assertEqual(self.mover._speed_z, new_speed)

    def test_z_lift_setter(self):
        new_lift = 40
        self.mover.z_lift = new_lift

        self.connected_stage.set_lift_distance.assert_called_once_with(
            new_lift)
        self.disconnected_stage.set_lift_distance.assert_not_called()
        self.assertEqual(self.mover._z_lift, new_lift)

    def test_speed_xy_getter_when_stored_speed_equals(self):
        expected_speed = 123.45
        self.mover._speed_xy = expected_speed
        self.connected_stage.get_speed_xy.return_value = expected_speed

        actual_speed = self.mover.speed_xy

        self.connected_stage.set_speed_xy.assert_not_called()
        self.disconnected_stage.set_speed_xy.assert_not_called()
        self.connected_stage.get_speed_xy.assert_called_once()
        self.disconnected_stage.get_speed_xy.assert_not_called()

        self.assertEqual(actual_speed, expected_speed)

    def test_seed_xy_getter_when_stored_speed_differ(self):
        expected_speed = 123.45
        stage_speed = 789.0
        self.mover._speed_xy = expected_speed
        self.connected_stage.get_speed_xy.return_value = stage_speed

        actual_speed = self.mover.speed_xy

        self.connected_stage.set_speed_xy.assert_called_once_with(
            expected_speed)
        self.disconnected_stage.set_speed_xy.assert_not_called()
        self.connected_stage.get_speed_xy.assert_called_once()
        self.disconnected_stage.get_speed_xy.assert_not_called()

        self.assertEqual(actual_speed, expected_speed)

    def test_speed_z_getter_when_stored_speed_equals(self):
        expected_speed = 123.45
        self.mover._speed_z = expected_speed
        self.connected_stage.get_speed_z.return_value = expected_speed

        actual_speed = self.mover.speed_z

        self.connected_stage.set_speed_z.assert_not_called()
        self.disconnected_stage.set_speed_z.assert_not_called()
        self.connected_stage.get_speed_z.assert_called_once()
        self.disconnected_stage.get_speed_z.assert_not_called()

        self.assertEqual(actual_speed, expected_speed)

    def test_seed_z_getter_when_stored_speed_differ(self):
        expected_speed = 123.45
        stage_speed = 789.0
        self.mover._speed_z = expected_speed
        self.connected_stage.get_speed_z.return_value = stage_speed

        actual_speed = self.mover.speed_z

        self.connected_stage.set_speed_z.assert_called_once_with(
            expected_speed)
        self.disconnected_stage.set_speed_z.assert_not_called()
        self.connected_stage.get_speed_z.assert_called_once()
        self.disconnected_stage.get_speed_z.assert_not_called()

        self.assertEqual(actual_speed, expected_speed)

    def test_z_lift_getter_when_stored_speed_equals(self):
        expected_lift = 500
        self.mover._z_lift = expected_lift
        self.connected_stage.get_lift_distance.return_value = expected_lift

        actual_lift = self.mover.z_lift

        self.connected_stage.set_lift_distance.assert_not_called()
        self.disconnected_stage.set_lift_distance.assert_not_called()
        self.connected_stage.get_lift_distance.assert_called_once()
        self.disconnected_stage.get_lift_distance.assert_not_called()

        self.assertEqual(actual_lift, expected_lift)

    def test_z_lift_getter_when_stored_speed_differ(self):
        expected_lift = 500
        stage_lift = 250
        self.mover._z_lift = expected_lift
        self.connected_stage.get_lift_distance.return_value = stage_lift

        actual_lift = self.mover.z_lift

        self.connected_stage.set_lift_distance.assert_called_once_with(
            expected_lift)
        self.disconnected_stage.set_lift_distance.assert_not_called()
        self.connected_stage.get_lift_distance.assert_called_once()
        self.disconnected_stage.get_lift_distance.assert_not_called()

        self.assertEqual(actual_lift, expected_lift)


class EmptyStagesCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expermiment_manager = Mock()
        with patch.object(Stage, 'discovery', return_value=[]):
            cls.mover = MoverNew(cls.expermiment_manager)

    @classmethod
    def tearDownClass(cls) -> None:
        del cls.expermiment_manager

    #
    #   Testing Decorators
    #

    def test_assert_connected_stages_calls_function(self):
        func = Mock()
        func.__name__ = 'Dummy Function'

        with self.assertRaises(MoverError):
            assert_connected_stages(func)(self.mover)

        func.assert_not_called()

    #
    #   Testing Mover Properties
    #

    def test_stage_filtering(self):
        self.assertListEqual(self.mover.connected_stages, [])
        self.assertListEqual(self.mover.disconnected_stages, [])

    def test_all_connected(self):
        self.assertFalse(self.mover.all_connected)

    def test_all_disconnected(self):
        self.assertTrue(self.mover.all_disconnected)

    #
    #   Testing Stage Connection
    #

    def test_connect_to_all_raises_error(self):
        with self.assertRaises(MoverError):
            self.mover.connect()

    def test_connect_to_stage_by_index_raises_error(self):
        with self.assertRaises(MoverError):
            self.mover.connect_stage_by_index(0)

    #
    #   Testing Mover Settings
    #

    def test_speed_xy_getter_raises_error(self):
        with self.assertRaises(MoverError):
            self.mover.speed_xy

    def test_speed_xy_setter(self):
        with self.assertRaises(MoverError):
            self.mover.speed_xy = 123.45

    def test_speed_z_setter(self):
        with self.assertRaises(MoverError):
            self.mover.speed_z = 123.45

    def test_z_lift_setter(self):
        with self.assertRaises(MoverError):
            self.mover.z_lift = 123.45


class AllConnectedPoolCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expermiment_manager = Mock()
        cls.connected_stage = Mock(connected=True)
        with patch.object(Stage, 'discovery', return_value=[cls.connected_stage]):
            cls.mover = MoverNew(cls.expermiment_manager)

    @classmethod
    def tearDownClass(cls) -> None:
        del cls.expermiment_manager

    def tearDown(self) -> None:
        self.connected_stage.reset_mock()

    #
    #   Testing Decorators
    #

    def test_assert_connected_stages_calls_function(self):
        func = Mock()
        func.__name__ = 'Dummy Function'

        assert_connected_stages(func)(self.mover)

        func.assert_called_once()

    #
    #   Testing Mover Properties
    #

    def test_stage_filtering(self):
        self.assertListEqual(
            self.mover.connected_stages, [
                self.connected_stage])
        self.assertListEqual(self.mover.disconnected_stages, [])

    def test_all_connected(self):
        self.assertTrue(self.mover.all_connected)

    def test_all_disconnected(self):
        self.assertFalse(self.mover.all_disconnected)


class AllDisconnectedPoolCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expermiment_manager = Mock()
        cls.disconnected_stage = Mock(connected=False)
        with patch.object(Stage, 'discovery', return_value=[cls.disconnected_stage]):
            cls.mover = MoverNew(cls.expermiment_manager)

    @classmethod
    def tearDownClass(cls) -> None:
        del cls.expermiment_manager

    def tearDown(self) -> None:
        self.disconnected_stage.reset_mock()

    #
    #   Testing Decorators
    #

    def test_assert_connected_stages_raises_error(self):
        func = Mock()
        func.__name__ = 'Dummy Function'

        with self.assertRaises(MoverError):
            assert_connected_stages(func)(self.mover)

        func.assert_not_called()

    #
    #   Testing Mover Properties
    #

    def test_stage_filtering(self):
        self.assertListEqual(self.mover.connected_stages, [])
        self.assertListEqual(
            self.mover.disconnected_stages, [
                self.disconnected_stage])

    def test_all_connected(self):
        self.assertFalse(self.mover.all_connected)

    def test_all_disconnected(self):
        self.assertTrue(self.mover.all_disconnected)

    #
    #   Testing Mover Settings
    #

    def test_speed_xy_setter(self):
        with self.assertRaises(MoverError):
            self.mover.speed_xy = 123.45

    def test_speed_z_setter(self):
        with self.assertRaises(MoverError):
            self.mover.speed_z = 123.45

    def test_z_lift_setter(self):
        with self.assertRaises(MoverError):
            self.mover.z_lift = 123.45
