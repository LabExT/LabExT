
from unittest import TestCase
from unittest.mock import Mock

import tkinter
import _tkinter

from LabExT.View.Controls.Wizard import Step, Wizard

class TKinterTestCase(TestCase):
    """These methods are going to be the same for every GUI test,
    so refactored them into a separate class
    """
    def setUp(self):
        self.root=tkinter.Tk()
        self.pump_events()

    def tearDown(self):
        if self.root:
            self.root.destroy()
            self.pump_events()

    def pump_events(self):
        while self.root.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
            pass


class WizardTest(TKinterTestCase):

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

    def test_wizard_build(self):
        self.assertEqual(self.wizard._next_button['text'], "Custom Next Label")
        self.assertEqual(self.wizard._previous_button['text'], "Custom Previous Label")
        self.assertEqual(self.wizard._cancel_button['text'], "Custom Cancel Label")
        self.assertEqual(self.wizard._finish_button['text'], "Custom Finish Label")

    
    def test_add_step_handle_callbacks(self):
        on_reload = Mock()
        on_next = Mock()
        on_previous = Mock()

        step = self.wizard.add_step(builder=lambda: None, on_reload=on_reload, on_next=on_next, on_previous=on_previous)

        step.on_next_callback()
        on_next.assert_called_once()

        step.on_previous_callback()
        on_previous.assert_called_once()

        step.on_reload_callback()
        on_reload.assert_called_once()

    
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


    def test_add_step_creates_new_sidebar_label(self):
        step = self.wizard.add_step(builder=lambda: None, title="My Custom Step")

        self.assertIsNotNone(step._sidebar_label)
        self.assertEqual(step._sidebar_label['text'], "My Custom Step")
        self.assertEqual(step._sidebar_label['foreground'], Step.INACTIVE_LABEL_COLOR)

        step.activate_sidebar_label()
        self.assertEqual(step._sidebar_label['foreground'], Step.ACTIVE_LABEL_COLOR)

        step.deactivate_sidebar_label()
        self.assertEqual(step._sidebar_label['foreground'], Step.INACTIVE_LABEL_COLOR)


    # Testing current step


    def test_next_step_if_next_step_is_present(self):
        on_next = Mock(return_value=False)
        current_step = self.wizard.add_step(builder=self.builder, on_next=on_next)
        self.wizard.current_step = current_step

        # Nothing happens, if current step has no next step
        self.wizard._next_button.invoke()

        on_next.assert_not_called()
        self.assertEqual(self.wizard.current_step, current_step)


    def test_next_step_if_next_step_callback_fails(self):
        on_next = Mock(return_value=False)
        next_builder = Mock()

        current_step = self.wizard.add_step(builder=self.builder, on_next=on_next)
        next_step = self.wizard.add_step(builder=next_builder)
        current_step.next_step = next_step

        self.wizard.current_step = current_step
        self.wizard._next_button.invoke()
        
        on_next.assert_called_once()
        self.assertEqual(self.wizard.current_step, current_step)
        next_builder.assert_not_called()


    def test_next_step_if_next_step_callback_succeeds(self):
        on_next = Mock(return_value=True)
        next_builder = Mock()

        current_step = self.wizard.add_step(builder=self.builder, on_next=on_next)
        next_step = self.wizard.add_step(builder=next_builder)
        current_step.next_step = next_step

        self.wizard.current_step = current_step
        self.wizard._next_button.invoke()
        
        on_next.assert_called_once()
        self.assertEqual(self.wizard.current_step, next_step)
        next_builder.assert_called_once()


    def test_previous_step_if_previous_step_is_present(self):
        on_previous = Mock(return_value=False)
        current_step = self.wizard.add_step(builder=self.builder, on_previous=on_previous)
        self.wizard.current_step = current_step

        # Nothing happens, if current step has no next step
        self.wizard._previous_button.invoke()

        on_previous.assert_not_called()
        self.assertEqual(self.wizard.current_step, current_step)


    def test_previous_step_if_previous_step_callback_fails(self):
        on_previous = Mock(return_value=False)
        previous_builder = Mock()

        current_step = self.wizard.add_step(builder=self.builder, on_previous=on_previous)
        previous_step = self.wizard.add_step(builder=previous_builder)
        current_step.previous_step = previous_step

        self.wizard.current_step = current_step
        self.wizard._previous_button.invoke()
        
        on_previous.assert_called_once()
        self.assertEqual(self.wizard.current_step, current_step)
        previous_builder.assert_not_called()


    def test_previous_step_if_previous_step_callback_succeeds(self):
        on_previous = Mock(return_value=True)
        previous_builder = Mock()

        current_step = self.wizard.add_step(builder=self.builder, on_previous=on_previous)
        previous_step = self.wizard.add_step(builder=previous_builder)
        current_step.previous_step = previous_step

        self.wizard.current_step = current_step
        self.wizard._previous_button.invoke()
        
        on_previous.assert_called_once()
        self.assertEqual(self.wizard.current_step, previous_step)
        previous_builder.assert_called_once()


    # def test_foo(self):
    #     w = Wizard(self.root)
    #     self.pump_events()

    # def test_enter(self):
    #     v = View_AskText(self.root,value=u"йцу")
    #     self.pump_events()
    #     v.e.focus_set()
    #     v.e.insert(tkinter.END,u'кен')
    #     v.e.event_generate('<Return>')
    #     self.pump_events()

    #     self.assertRaises(tkinter.TclError, lambda: v.top.winfo_viewable())
    #     self.assertEqual(v.value,u'йцукен')
