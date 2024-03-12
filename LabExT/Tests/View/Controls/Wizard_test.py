#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from unittest.mock import Mock
import pytest
from LabExT.Tests.Utils import TKinterTestCase

import tkinter
from LabExT.View.Controls.Wizard import Step, Wizard


class WizardUnitTest(TKinterTestCase):
    """
    Unittests for Wizard Widget.

    These tests do not test appearance, but functionality.
    """

    def setUp(self):
        super().setUp()
        self.wizard = Wizard(
            self.root,
            next_button_label="Custom Next Label",
            previous_button_label="Custom Previous Label",
            cancel_button_label="Custom Cancel Label",
            finish_button_label="Custom Finish Label"
        )
        self.builder = Mock()

    @pytest.mark.flaky(reruns=3)
    def test_wizard_build(self):
        self.assertEqual(self.wizard._next_button['text'], "Custom Next Label")
        self.assertEqual(
            self.wizard._previous_button['text'],
            "Custom Previous Label")
        self.assertEqual(
            self.wizard._cancel_button['text'],
            "Custom Cancel Label")
        self.assertEqual(
            self.wizard._finish_button['text'],
            "Custom Finish Label")

    @pytest.mark.flaky(reruns=3)
    def test_add_step_handle_callbacks(self):
        on_reload = Mock()
        on_next = Mock()
        on_previous = Mock()

        step = self.wizard.add_step(
            builder=lambda: None,
            on_reload=on_reload,
            on_next=on_next,
            on_previous=on_previous)

        step.on_next_callback()
        on_next.assert_called_once()

        step.on_previous_callback()
        on_previous.assert_called_once()

        step.on_reload_callback()
        on_reload.assert_called_once()

    @pytest.mark.flaky(reruns=3)
    def test_add_step_handle_step_linking(self):
        step = self.wizard.add_step(builder=lambda: None)
        previous_step = self.wizard.add_step(builder=lambda: None)
        next_step = self.wizard.add_step(builder=lambda: None)

        # Link Three step as a chain
        previous_step.next_step = step
        step.previous_step = previous_step
        step.next_step = next_step
        next_step.previous_step = step

        # Check if previous_step knows all its linkings
        self.assertFalse(previous_step.previous_step_available)
        self.assertIsNone(previous_step.previous_step)
        self.assertTrue(previous_step.next_step_available)
        self.assertEqual(previous_step.next_step, step)

        # Check if step knows all its linkings
        self.assertTrue(step.previous_step_available)
        self.assertEqual(step.previous_step, previous_step)
        self.assertTrue(step.next_step_available)
        self.assertEqual(step.next_step, next_step)

        # Check if next_step knows all its linkings
        self.assertTrue(next_step.previous_step_available)
        self.assertEqual(next_step.previous_step, step)
        self.assertFalse(next_step.next_step_available)
        self.assertIsNone(next_step.next_step)

    @pytest.mark.flaky(reruns=3)
    def test_add_step_creates_new_sidebar_label(self):
        step = self.wizard.add_step(
            builder=lambda: None,
            title="My Custom Step")

        self.assertIsNotNone(step._sidebar_label)
        self.assertEqual(step._sidebar_label['text'], "My Custom Step")
        self.assertEqual(
            step._sidebar_label['foreground'],
            Step.INACTIVE_LABEL_COLOR)

        step.activate_sidebar_label()
        self.assertEqual(
            step._sidebar_label['foreground'],
            Step.ACTIVE_LABEL_COLOR)

        step.deactivate_sidebar_label()
        self.assertEqual(
            step._sidebar_label['foreground'],
            Step.INACTIVE_LABEL_COLOR)

    # Testing current step
    @pytest.mark.flaky(reruns=3)
    def test_next_step_if_next_step_is_present(self):
        on_next = Mock(return_value=False)
        current_step = self.wizard.add_step(
            builder=self.builder, on_next=on_next)
        self.wizard.current_step = current_step

        # Nothing happens, if current step has no next step
        self.wizard._next_button.invoke()
        self.pump_events()

        on_next.assert_not_called()
        self.assertEqual(self.wizard.current_step, current_step)

    @pytest.mark.flaky(reruns=3)
    def test_next_step_if_next_step_callback_fails(self):
        on_next = Mock(return_value=False)
        next_builder = Mock()

        current_step = self.wizard.add_step(
            builder=self.builder, on_next=on_next)
        next_step = self.wizard.add_step(builder=next_builder)
        current_step.next_step = next_step

        self.wizard.current_step = current_step
        self.wizard._next_button.invoke()
        self.pump_events()

        on_next.assert_called_once()
        self.assertEqual(self.wizard.current_step, current_step)
        next_builder.assert_not_called()

    @pytest.mark.flaky(reruns=3)
    def test_next_step_if_next_step_callback_succeeds(self):
        on_next = Mock(return_value=True)
        next_builder = Mock()

        current_step = self.wizard.add_step(
            builder=self.builder, on_next=on_next)
        next_step = self.wizard.add_step(builder=next_builder)
        current_step.next_step = next_step

        self.wizard.current_step = current_step
        self.wizard._next_button.invoke()
        self.pump_events()

        on_next.assert_called_once()
        self.assertEqual(self.wizard.current_step, next_step)
        next_builder.assert_called_once()

    @pytest.mark.flaky(reruns=3)
    def test_previous_step_if_previous_step_is_present(self):
        on_previous = Mock(return_value=False)
        current_step = self.wizard.add_step(
            builder=self.builder, on_previous=on_previous)
        self.wizard.current_step = current_step

        # Nothing happens, if current step has no next step
        self.wizard._previous_button.invoke()
        self.pump_events()

        on_previous.assert_not_called()
        self.assertEqual(self.wizard.current_step, current_step)

    @pytest.mark.flaky(reruns=3)
    def test_previous_step_if_previous_step_callback_fails(self):
        on_previous = Mock(return_value=False)
        previous_builder = Mock()

        current_step = self.wizard.add_step(
            builder=self.builder, on_previous=on_previous)
        previous_step = self.wizard.add_step(builder=previous_builder)
        current_step.previous_step = previous_step

        self.wizard.current_step = current_step
        self.wizard._previous_button.invoke()
        self.pump_events()

        on_previous.assert_called_once()
        self.assertEqual(self.wizard.current_step, current_step)
        previous_builder.assert_not_called()

    @pytest.mark.flaky(reruns=3)
    def test_previous_step_if_previous_step_callback_succeeds(self):
        on_previous = Mock(return_value=True)
        previous_builder = Mock()

        current_step = self.wizard.add_step(
            builder=self.builder, on_previous=on_previous)
        previous_step = self.wizard.add_step(builder=previous_builder)
        current_step.previous_step = previous_step

        self.wizard.current_step = current_step
        self.wizard._previous_button.invoke()
        self.pump_events()

        on_previous.assert_called_once()
        self.assertEqual(self.wizard.current_step, previous_step)
        previous_builder.assert_called_once()

    @pytest.mark.flaky(reruns=3)
    def test_current_step_changes_sidebar_config(self):
        current_step = self.wizard.add_step(
            builder=self.builder, title="Current Step")
        self.wizard._current_step = current_step

        step = self.wizard.add_step(
            builder=self.builder,
            title="My Custom Step")
        self.wizard.current_step = step

        self.assertEqual(
            current_step._sidebar_label['foreground'],
            Step.INACTIVE_LABEL_COLOR)
        self.assertEqual(
            step._sidebar_label['foreground'],
            Step.ACTIVE_LABEL_COLOR)
        self.assertEqual(self.wizard.current_step, step)

    @pytest.mark.flaky(reruns=3)
    def test_current_step_renders_new_frame(self):
        current_step = self.wizard.add_step(
            builder=self.builder, title="Current Step")
        self.wizard.current_step = current_step

        self.builder.assert_called_once()

    @pytest.mark.flaky(reruns=3)
    def test_current_step_calls_reload_callback(self):
        on_reload = Mock()

        current_step = self.wizard.add_step(
            builder=self.builder, on_reload=on_reload)
        self.wizard.current_step = current_step

        on_reload.assert_called_once()


class WizardIntegrationTest(TKinterTestCase):
    """
    Integration test for a Wizard with 2 steps.
    """

    def setUp(self):
        super().setUp()

        self.on_finish = Mock()
        self.on_cancel = Mock()
        self.wizard = Wizard(
            self.root,
            on_cancel=self.on_cancel,
            on_finish=self.on_finish)

        self.first_step_builder = Mock()
        self.first_step_on_reload = Mock()
        self.first_step_on_next = Mock()
        self.first_step_on_previous = Mock()
        self.first_step = self.wizard.add_step(
            builder=self.first_step_builder,
            on_next=self.first_step_on_next,
            on_previous=self.first_step_on_previous,
            on_reload=self.first_step_on_reload,
            title="First Step"
        )

        self.second_step_builder = Mock()
        self.second_step_on_reload = Mock()
        self.second_step_on_next = Mock()
        self.second_step_on_previous = Mock()
        self.second_step = self.wizard.add_step(
            builder=self.second_step_builder,
            on_next=self.second_step_on_next,
            on_previous=self.second_step_on_previous,
            on_reload=self.second_step_on_reload,
            title="Second Step"
        )

        self.first_step.next_step = self.second_step
        self.second_step.previous_step = self.first_step

    def assertSidebarLabelColor(self, first_step, second_step):
        self.assertEqual(
            self.first_step._sidebar_label['foreground'],
            first_step)
        self.assertEqual(
            self.second_step._sidebar_label['foreground'],
            second_step)

    def assertButtonState(
            self,
            next=tkinter.NORMAL,
            previous=tkinter.NORMAL,
            cancel=tkinter.NORMAL,
            finish=tkinter.NORMAL):
        self.assertEqual(self.wizard._next_button['state'], next)
        self.assertEqual(self.wizard._previous_button['state'], previous)
        self.assertEqual(self.wizard._cancel_button['state'], cancel)
        self.assertEqual(self.wizard._finish_button['state'], finish)

    @pytest.mark.flaky(reruns=3)
    def test_next_from_first_step(self):
        self.wizard.current_step = self.first_step

        self.first_step_builder.assert_called_once()
        self.first_step_on_reload.assert_called_once()
        self.assertSidebarLabelColor(
            first_step=Step.ACTIVE_LABEL_COLOR,
            second_step=Step.INACTIVE_LABEL_COLOR
        )
        self.assertButtonState(
            previous=tkinter.DISABLED,
            next=tkinter.NORMAL,
            finish=tkinter.DISABLED
        )

        # Move to next step
        self.wizard._next_button.invoke()
        self.pump_events()

        self.first_step_on_next.assert_called_once()
        self.second_step_builder.assert_called_once()
        self.second_step_on_reload.assert_called_once()

        self.assertSidebarLabelColor(
            first_step=Step.INACTIVE_LABEL_COLOR,
            second_step=Step.ACTIVE_LABEL_COLOR
        )
        self.assertButtonState(
            previous=tkinter.NORMAL,
            next=tkinter.DISABLED,
            finish=tkinter.DISABLED
        )

    @pytest.mark.flaky(reruns=3)
    def test_previous_from_first_step(self):
        self.wizard.current_step = self.first_step

        # Move to previous step
        self.wizard._previous_button.invoke()
        self.pump_events()

        self.first_step_builder.assert_called_once()
        self.first_step_on_previous.assert_not_called()
        self.assertSidebarLabelColor(
            first_step=Step.ACTIVE_LABEL_COLOR,
            second_step=Step.INACTIVE_LABEL_COLOR
        )
        self.assertButtonState(
            previous=tkinter.DISABLED,
            next=tkinter.NORMAL,
            finish=tkinter.DISABLED
        )

    @pytest.mark.flaky(reruns=3)
    def test_next_from_second_step(self):
        self.wizard.current_step = self.second_step

        # Move to next step
        self.wizard._next_button.invoke()
        self.pump_events()

        self.second_step_builder.assert_called_once()
        self.second_step_on_next.assert_not_called()
        self.assertSidebarLabelColor(
            first_step=Step.INACTIVE_LABEL_COLOR,
            second_step=Step.ACTIVE_LABEL_COLOR
        )
        self.assertButtonState(
            previous=tkinter.NORMAL,
            next=tkinter.DISABLED,
            finish=tkinter.DISABLED
        )

    @pytest.mark.flaky(reruns=3)
    def test_previous_from_second_step(self):
        self.wizard.current_step = self.second_step

        self.second_step_builder.assert_called_once()
        self.second_step_on_reload.assert_called_once()
        self.assertSidebarLabelColor(
            first_step=Step.INACTIVE_LABEL_COLOR,
            second_step=Step.ACTIVE_LABEL_COLOR
        )
        self.assertButtonState(
            previous=tkinter.NORMAL,
            next=tkinter.DISABLED,
            finish=tkinter.DISABLED
        )

        # Move to next step
        self.wizard._previous_button.invoke()
        self.pump_events()

        self.second_step_on_previous.assert_called_once()
        self.first_step_builder.assert_called_once()
        self.first_step_on_reload.assert_called_once()

        self.assertSidebarLabelColor(
            first_step=Step.ACTIVE_LABEL_COLOR,
            second_step=Step.INACTIVE_LABEL_COLOR
        )
        self.assertButtonState(
            previous=tkinter.DISABLED,
            next=tkinter.NORMAL,
            finish=tkinter.DISABLED
        )

    @pytest.mark.flaky(reruns=3)
    def test_finish(self):
        self.wizard.current_step = self.first_step
        self.first_step.finish_step_enabled = False

        self.assertEqual(self.wizard._finish_button['state'], tkinter.DISABLED)

        self.wizard._finish_button.invoke()
        self.pump_events()

        self.on_finish.assert_not_called()

        self.first_step.finish_step_enabled = True
        self.wizard.__reload__()

        self.assertEqual(self.wizard._finish_button['state'], tkinter.NORMAL)

        self.wizard._finish_button.invoke()
        self.pump_events()

        self.on_finish.assert_called_once()

    @pytest.mark.flaky(reruns=3)
    def test_cancel(self):
        self.wizard.current_step = self.first_step

        self.wizard._cancel_button.invoke()
        self.pump_events()

        self.on_cancel.assert_called_once()
