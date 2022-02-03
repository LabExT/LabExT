#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2022  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

SA_OK                               =       0
SA_INITIALIZATION_ERROR             =       1
SA_NOT_INITIALIZED_ERROR            =       2
SA_NO_SYSTEMS_FOUND_ERROR           =       3
SA_TOO_MANY_SYSTEMS_ERROR           =       4
SA_INVALID_SYSTEM_INDEX_ERROR       =       5
SA_INVALID_CHANNEL_INDEX_ERROR      =       6
SA_TRANSMIT_ERROR                   =       7
SA_WRITE_ERROR                      =       8
SA_INVALID_PARAMETER_ERROR          =       9
SA_READ_ERROR                       =       10
SA_INTERNAL_ERROR                   =       12
SA_WRONG_MODE_ERROR                 =       13
SA_PROTOCOL_ERROR                   =       14
SA_TIMEOUT_ERROR                    =       15
SA_ID_LIST_TOO_SMALL_ERROR          =       17
SA_SYSTEM_ALREADY_ADDED_ERROR       =       18
SA_WRONG_CHANNEL_TYPE_ERROR         =       19
SA_CANCELED_ERROR                   =       20
SA_INVALID_SYSTEM_LOCATOR_ERROR     =       21
SA_INPUT_BUFFER_OVERFLOW_ERROR      =       22
SA_QUERYBUFFER_SIZE_ERROR           =       23
SA_DRIVER_ERROR                     =       24
SA_NO_SUCH_SLAVE_ERROR              =       128
SA_NO_SENSOR_PRESENT_ERROR          =       129
SA_AMPLITUDE_TOO_LOW_ERROR          =       130
SA_AMPLITUDE_TOO_HIGH_ERROR         =       131
SA_FREQUENCY_TOO_LOW_ERROR          =       132
SA_FREQUENCY_TOO_HIGH_ERROR         =       133
SA_SCAN_TARGET_TOO_HIGH_ERROR       =       135
SA_SCAN_SPEED_TOO_LOW_ERROR         =       136
SA_SCAN_SPEED_TOO_HIGH_ERROR        =       137
SA_SENSOR_DISABLED_ERROR            =       140
SA_COMMAND_OVERRIDDEN_ERROR         =       141
SA_END_STOP_REACHED_ERROR           =       142
SA_WRONG_SENSOR_TYPE_ERROR          =       143
SA_COULD_NOT_FIND_REF_ERROR         =       144
SA_WRONG_END_EFFECTOR_TYPE_ERROR    =       145
SA_MOVEMENT_LOCKED_ERROR            =       146
SA_RANGE_LIMIT_REACHED_ERROR        =       147
SA_PHYSICAL_POSITION_UNKNOWN_ERROR  =       148
SA_OUTPUT_BUFFER_OVERFLOW_ERROR     =       149
SA_COMMAND_NOT_PROCESSABLE_ERROR    =       150
SA_WAITING_FOR_TRIGGER_ERROR        =       151
SA_COMMAND_NOT_TRIGGERABLE_ERROR    =       152
SA_COMMAND_QUEUE_FULL_ERROR         =       153
SA_INVALID_COMPONENT_ERROR          =       154
SA_INVALID_SUB_COMPONENT_ERROR      =       155
SA_INVALID_PROPERTY_ERROR           =       156
SA_PERMISSION_DENIED_ERROR          =       157
SA_CALIBRATION_FAILED_ERROR         =       160
SA_UNKNOWN_COMMAND_ERROR            =       240
SA_OTHER_ERROR                      =       255

# general definitions
SA_UNDEFINED                        =       0
SA_FALSE                            =       0
SA_TRUE                             =       1
SA_DISABLED                         =       0
SA_ENABLED                          =       1
SA_FALLING_EDGE                     =       0
SA_RISING_EDGE                      =       1
SA_FORWARD                          =       0
SA_BACKWARD                         =       1

# component selectors
SA_GENERAL                          =       1
SA_DIGITAL_IN                       =       2
SA_ANALOG_IN                        =       3
SA_COUNTER                          =       4
SA_CAPTURE_BUFFER                   =       5
SA_COMMAND_QUEUE                    =       6
SA_SOFTWARE_TRIGGER                 =       7
SA_SENSOR                           =       8
SA_MONITOR                          =       9

# component sub selectors
SA_EMERGENCY_STOP                   =       1
SA_LOW_VIBRATION                    =       2

SA_BROADCAST_STOP                   =       4
SA_POSITION_CONTROL                 =       5

SA_REFERENCE_SIGNAL                 =       7

SA_POWER_SUPPLY                     =       11

SA_SCALE                            =       22
SA_ANALOG_AUX_SIGNAL                =       23

# component properties
SA_OPERATION_MODE                   =       1
SA_ACTIVE_EDGE                      =       2
SA_TRIGGER_SOURCE                   =       3
SA_SIZE                             =       4
SA_VALUE                            =       5
SA_CAPACITY                         =       6
SA_DIRECTION                        =       7
SA_SETPOINT                         =       8
SA_P_GAIN                           =       9
SA_P_RIGHT_SHIFT                    =       10
SA_I_GAIN                           =       11
SA_I_RIGHT_SHIFT                    =       12
SA_D_GAIN                           =       13
SA_D_RIGHT_SHIFT                    =       14
SA_ANTI_WINDUP                      =       15
SA_PID_LIMIT                        =       16
SA_FORCED_SLIP                      =       17

SA_THRESHOLD                        =       38
SA_DEFAULT_OPERATION_MODE           =       45

SA_OFFSET                           =       47
SA_DISTANCE_TO_REF_MARK             =       48
SA_REFERENCE_SPEED                  =       49

# operation mode property values for SA_EMERGENCY_STOP sub selector
SA_ESM_NORMAL                       =       0
SA_ESM_RESTRICTED                   =       1
SA_ESM_DISABLED                     =       2
SA_ESM_AUTO_RELEASE                 =       3

# configuration flags for SA_InitDevices
SA_SYNCHRONOUS_COMMUNICATION        =       0
SA_ASYNCHRONOUS_COMMUNICATION       =       1
SA_HARDWARE_RESET                   =       2

# return values from SA_GetInitState
SA_INIT_STATE_NONE                  =       0
SA_INIT_STATE_SYNC                  =       1
SA_INIT_STATE_ASYNC                 =       2

# return values for SA_GetChannelType
SA_POSITIONER_CHANNEL_TYPE          =       0
SA_END_EFFECTOR_CHANNEL_TYPE        =       1

# Hand Control Module modes for SA_SetHCMEnabled
SA_HCM_DISABLED                     =       0
SA_HCM_ENABLED                      =       1
SA_HCM_CONTROLS_DISABLED            =       2

# configuration values for SA_SetBufferedOutput_A
SA_UNBUFFERED_OUTPUT                =       0
SA_BUFFERED_OUTPUT                  =       1

# configuration values for SA_SetStepWhileScan_X
SA_NO_STEP_WHILE_SCAN               =       0
SA_STEP_WHILE_SCAN                  =       1

# configuration values for SA_SetAccumulateRelativePositions_X
SA_NO_ACCUMULATE_RELATIVE_POSITIONS =       0
SA_ACCUMULATE_RELATIVE_POSITIONS    =       1

# configuration values for SA_SetSensorEnabled_X
SA_SENSOR_DISABLED                  =       0
SA_SENSOR_ENABLED                   =       1
SA_SENSOR_POWERSAVE                 =       2

# movement directions for SA_FindReferenceMark_X
SA_FORWARD_DIRECTION                     		= 0
SA_BACKWARD_DIRECTION                    		= 1
SA_FORWARD_BACKWARD_DIRECTION            		= 2
SA_BACKWARD_FORWARD_DIRECTION            		= 3
SA_FORWARD_DIRECTION_ABORT_ON_ENDSTOP    		= 4
SA_BACKWARD_DIRECTION_ABORT_ON_ENDSTOP   		= 5
SA_FORWARD_BACKWARD_DIRECTION_ABORT_ON_ENDSTOP 	= 6
SA_BACKWARD_FORWARD_DIRECTION_ABORT_ON_ENDSTOP 	= 7

# configuration values for SA_FindReferenceMark_X
SA_NO_AUTO_ZERO                     =       0
SA_AUTO_ZERO                        =       1

# return values for SA_GetPhyscialPositionKnown_X
SA_PHYSICAL_POSITION_UNKNOWN        =       0
SA_PHYSICAL_POSITION_KNOWN          =       1

# infinite timeout for functions that wait
SA_TIMEOUT_INFINITE                 =       0xFFFFFFFF

# sensor types for SA_SetSensorType_X and SA_GetSensorType_X
SA_NO_SENSOR_TYPE                   =       0
SA_S_SENSOR_TYPE                    =       1
SA_SR_SENSOR_TYPE                   =       2
SA_ML_SENSOR_TYPE                   =       3
SA_MR_SENSOR_TYPE                   =       4
SA_SP_SENSOR_TYPE                   =       5
SA_SC_SENSOR_TYPE                   =       6
SA_M25_SENSOR_TYPE                  =       7
SA_SR20_SENSOR_TYPE                 =       8
SA_M_SENSOR_TYPE                    =       9
SA_GC_SENSOR_TYPE                   =       10
SA_GD_SENSOR_TYPE                   =       11
SA_GE_SENSOR_TYPE                   =       12
SA_RA_SENSOR_TYPE                   =       13
SA_GF_SENSOR_TYPE                   =       14
SA_RB_SENSOR_TYPE                   =       15
SA_G605S_SENSOR_TYPE                =       16
SA_G775S_SENSOR_TYPE                =       17
SA_SC500_SENSOR_TYPE                =       18
SA_G955S_SENSOR_TYPE                =       19
SA_SR77_SENSOR_TYPE                 =       20
SA_SD_SENSOR_TYPE                   =       21
SA_R20ME_SENSOR_TYPE                =       22
SA_SR2_SENSOR_TYPE                  =       23
SA_SCD_SENSOR_TYPE                  =       24
SA_SRC_SENSOR_TYPE                  =       25
SA_SR36M_SENSOR_TYPE                =       26
SA_SR36ME_SENSOR_TYPE               =       27
SA_SR50M_SENSOR_TYPE                =       28
SA_SR50ME_SENSOR_TYPE               =       29
SA_G1045S_SENSOR_TYPE               =       30
SA_G1395S_SENSOR_TYPE               =       31
SA_MD_SENSOR_TYPE                   =       32
SA_G935M_SENSOR_TYPE                =       33
SA_SHL20_SENSOR_TYPE                =       34
SA_SCT_SENSOR_TYPE                  =       35
SA_SR77T_SENSOR_TYPE                =       36
SA_SR120_SENSOR_TYPE                =       37
SA_LC_SENSOR_TYPE                   =       38
SA_LR_SENSOR_TYPE                   =       39
SA_LCD_SENSOR_TYPE                  =       40
SA_L_SENSOR_TYPE                    =       41
SA_LD_SENSOR_TYPE                   =       42
SA_LE_SENSOR_TYPE                   =       43
SA_LED_SENSOR_TYPE                  =       44
SA_GDD_SENSOR_TYPE                  =       45
SA_GED_SENSOR_TYPE                  =       46
SA_G935S_SENSOR_TYPE                =       47
SA_G605DS_SENSOR_TYPE               =       48
SA_G775DS_SENSOR_TYPE               =       49

# end effector types for SA_SetEndEffectorType_X and SA_GetEndEffectorType_X
SA_ANALOG_SENSOR_END_EFFECTOR_TYPE  =       0
SA_GRIPPER_END_EFFECTOR_TYPE        =       1
SA_FORCE_SENSOR_END_EFFECTOR_TYPE   =       2
SA_FORCE_GRIPPER_END_EFFECTOR_TYPE  =       3

# packet types for asynchronous mode
SA_NO_PACKET_TYPE                       =   0
SA_ERROR_PACKET_TYPE                    =   1
SA_POSITION_PACKET_TYPE                 =   2
SA_COMPLETED_PACKET_TYPE                =   3
SA_STATUS_PACKET_TYPE                   =   4
SA_ANGLE_PACKET_TYPE                    =   5
SA_VOLTAGE_LEVEL_PACKET_TYPE            =   6
SA_SENSOR_TYPE_PACKET_TYPE              =   7
SA_SENSOR_ENABLED_PACKET_TYPE           =   8
SA_END_EFFECTOR_TYPE_PACKET_TYPE        =   9
SA_GRIPPER_OPENING_PACKET_TYPE          =   10
SA_FORCE_PACKET_TYPE                    =   11
SA_MOVE_SPEED_PACKET_TYPE               =   12
SA_PHYSICAL_POSITION_KNOWN_PACKET_TYPE  =   13
SA_POSITION_LIMIT_PACKET_TYPE           =   14
SA_ANGLE_LIMIT_PACKET_TYPE              =   15
SA_SAFE_DIRECTION_PACKET_TYPE           =   16
SA_SCALE_PACKET_TYPE                    =   17
SA_MOVE_ACCELERATION_PACKET_TYPE        =   18
SA_CHANNEL_PROPERTY_PACKET_TYPE         =   19
SA_CAPTURE_BUFFER_PACKET_TYPE           =   20
SA_TRIGGERED_PACKET_TYPE                =   21
SA_INVALID_PACKET_TYPE                  =   255

# channel status codes
SA_STOPPED_STATUS                       =   0
SA_STEPPING_STATUS                      =   1
SA_SCANNING_STATUS                      =   2
SA_HOLDING_STATUS                       =   3
SA_TARGET_STATUS                        =   4
SA_MOVE_DELAY_STATUS                    =   5
SA_CALIBRATING_STATUS                   =   6
SA_FINDING_REF_STATUS                   =   7
SA_OPENING_STATUS                       =   8

# compatibility definitions
SA_NO_REPORT_ON_COMPLETE                =   0
SA_REPORT_ON_COMPLETE                   =   1



def SA_DSV(value, selector, subSelector): pass
def SA_EPK(selector, subSelector, proper): pass
def SA_ESV(selector, subSelector): pass
def SA_GetStatusInfo(status, info): pass


def SA_OpenSystem(systemIndex,locator,options): pass
def SA_CloseSystem(systemIndex): pass
def SA_FindSystems(options,outBuffer,ioBufferSize): pass
def SA_GetSystemLocator(systemIndex, outBuffer, ioBufferSize): pass
def SA_AddSystemToInitSystemsList(systemId): pass
def SA_ClearInitSystemsList(): pass
def SA_GetAvailableSystems(idList, idListSize): pass
def SA_InitSystems(configuration): pass
def SA_ReleaseSystems(): pass
def SA_GetInitState(initMode): pass
def SA_GetNumberOfSystems(number): pass
def SA_GetSystemID(systemIndex, systemId): pass
def SA_GetChannelType(systemIndex, channelIndex, typ): pass
def SA_GetDLLVersion(version): pass
def SA_GetNumberOfChannels(systemIndex, channels): pass
def SA_SetHCMEnabled(systemIndex, enabled): pass

def SA_GetAngleLimit_S(systemIndex, channelIndex, minAngle, minRevolution, maxAngle, maxRevolution): pass
def SA_GetChannelProperty_S(systemIndex, channelIndex, key, value): pass
def SA_GetClosedLoopMoveAcceleration_S(systemIndex, channelIndex, acceleration): pass
def SA_GetClosedLoopMoveSpeed_S(systemIndex, channelIndex, speed): pass
def SA_GetEndEffectorType_S(systemIndex, channelIndex, typ, param1, param2): pass
def SA_GetPositionLimit_S(systemIndex, channelIndex, minPosition, maxPosition): pass
def SA_GetSafeDirection_S(systemIndex, channelIndex, direction): pass
def SA_GetScale_S(systemIndex, channelIndex, scale, inverted): pass
def SA_GetSensorEnabled_S(systemIndex, enabled): pass
def SA_GetSensorType_S(systemIndex, channelIndex, typ): pass
def SA_SetAccumulateRelativePositions_S(systemIndex, channelIndex, accumulate): pass
def SA_SetAngleLimit_S(systemIndex, channelIndex, minAngle, minRevolution, maxAngle, maxRevolution): pass
def SA_SetChannelProperty_S(systemIndex, channelIndex, key, value): pass
def SA_SetClosedLoopMaxFrequency_S(systemIndex, channelIndex, frequency): pass
def SA_SetClosedLoopMoveAcceleration_S(systemIndex, channelIndex, acceleration): pass
def SA_SetClosedLoopMoveSpeed_S(systemIndex, channelIndex, speed): pass
def SA_SetEndEffectorType_S(systemIndex, channelIndex, typ, param1, param2): pass
def SA_SetPosition_S(systemIndex, channelIndex, position): pass
def SA_SetPositionLimit_S(systemIndex, channelIndex, minPosition, maxPosition): pass
def SA_SetSafeDirection_S(systemIndex, channelIndex, direction): pass
def SA_SetScale_S(systemIndex, channelIndex, scale, inverted): pass
def SA_SetSensorEnabled_S(systemIndex, enabled): pass
def SA_SetSensorType_S(systemIndex, channelIndex, typ): pass
def SA_SetStepWhileScan_S(systemIndex, channelIndex, step): pass
def SA_SetZeroForce_S(systemIndex, channelIndex): pass

def SA_CalibrateSensor_S(systemIndex, channelIndex): pass
def SA_FindReferenceMark_S(systemIndex, channelIndex, direction, holdTime, autoZero): pass
def SA_GotoAngleAbsolute_S(systemIndex, channelIndex, angle, revolution, holdTime): pass
def SA_GotoAngleRelative_S(systemIndex, channelIndex, angleDiff, revolutionDiff, holdTime): pass
def SA_GotoGripperForceAbsolute_S(systemIndex, channelIndex, force, speed, holdTime): pass
def SA_GotoGripperOpeningAbsolute_S(systemIndex, channelIndex, opening, speed): pass
def SA_GotoGripperOpeningRelative_S(systemIndex, channelIndex, diff, speed): pass
def SA_GotoPositionAbsolute_S(systemIndex, channelIndex, position, holdTime): pass
def SA_GotoPositionRelative_S(systemIndex, channelIndex, diff, holdTime): pass
def SA_ScanMoveAbsolute_S(systemIndex, channelIndex, target, scanSpeed): pass
def SA_ScanMoveRelative_S(systemIndex, channelIndex, diff, scanSpeed): pass
def SA_StepMove_S(systemIndex, channelIndex, steps, amplitude, frequency): pass
def SA_Stop_S(systemIndex, channelIndex): pass

def SA_GetAngle_S(systemIndex, channelIndex, angle, revolution): pass
def SA_GetCaptureBuffer_S(systemIndex, channelIndex, bufferIndex, buffr): pass
def SA_GetForce_S(systemIndex, channelIndex, force): pass
def SA_GetGripperOpening_S(systemIndex, channelIndex, opening): pass
def SA_GetPhysicalPositionKnown_S(systemIndex, channelIndex, known): pass
def SA_GetPosition_S(systemIndex, channelIndex, position): pass
def SA_GetStatus_S(systemIndex, channelIndex, status): pass
def SA_GetVoltageLevel_S(systemIndex, channelIndex, level): pass

def SA_AppendTriggeredCommand_A(systemIndex, channelIndex, triggerSource): pass
def SA_ClearTriggeredCommandQueue_A(systemIndex, channelIndex): pass
def SA_FlushOutput_A(systemIndex): pass
def SA_GetAngleLimit_A(systemIndex, channelIndex): pass
def SA_GetBufferedOutput_A(systemIndex, mode): pass
def SA_GetChannelProperty_A(systemIndex, channelIndex, key): pass
def SA_GetClosedLoopMoveAcceleration_A(systemIndex, channelIndex): pass
def SA_GetClosedLoopMoveSpeed_A(systemIndex, channelIndex): pass
def SA_GetEndEffectorType_A(systemIndex, channelIndex): pass
def SA_GetPhysicalPositionKnown_A(systemIndex, channelIndex): pass
def SA_GetPositionLimit_A(systemIndex, channelIndex): pass
def SA_GetSafeDirection_A(systemIndex, channelIndex): pass
def SA_GetScale_A(systemIndex, channelIndex): pass
def SA_GetSensorEnabled_A(systemIndex): pass
def SA_GetSensorType_A(systemIndex, channelIndex): pass
def SA_SetAccumulateRelativePositions_A(systemIndex, channelIndex, accumulate): pass
def SA_SetAngleLimit_A(systemIndex, channelIndex, minAngle, minRevolution, maxAngle, maxRevolution): pass
def SA_SetBufferedOutput_A(systemIndex, mode): pass
def SA_SetChannelProperty_A(systemIndex, channelIndex, key, value): pass
def SA_SetClosedLoopMaxFrequency_A(systemIndex, channelIndex, frequency): pass
def SA_SetClosedLoopMoveAcceleration_A(systemIndex, channelIndex, acceleration): pass
def SA_SetClosedLoopMoveSpeed_A(systemIndex, channelIndex, speed): pass
def SA_SetEndEffectorType_A(systemIndex, channelIndex, typ, param1, param2): pass
def SA_SetPosition_A(systemIndex, channelIndex, position): pass
def SA_SetPositionLimit_A(systemIndex, channelIndex, minPosition, maxPosition): pass
def SA_SetReportOnComplete_A(systemIndex, channelIndex, report): pass
def SA_SetReportOnTriggered_A(systemIndex, channelIndex, report): pass
def SA_SetSafeDirection_A(systemIndex, channelIndex, direction): pass
def SA_SetScale_A(systemIndex, channelIndex, scale, inverted): pass
def SA_SetSensorEnabled_A(systemIndex, enabled): pass
def SA_SetSensorType_A(systemIndex, channelIndex, typ): pass
def SA_SetStepWhileScan_A(systemIndex, channelIndex, step): pass
def SA_SetZeroForce_A(systemIndex, channelIndex): pass

def SA_CalibrateSensor_A(systemIndex, channelIndex): pass
def SA_FindReferenceMark_A(systemIndex, channelIndex, direction, holdTime, autoZero): pass
def SA_GotoAngleAbsolute_A(systemIndex, channelIndex, angle, revolution, holdTime): pass
def SA_GotoAngleRelative_A(systemIndex, channelIndex, angleDiff, revolutionDiff, holdTime): pass
def SA_GotoGripperForceAbsolute_A(systemIndex, channelIndex, force, speed, holdTime): pass
def SA_GotoGripperOpeningAbsolute_A(systemIndex, channelIndex, opening, speed): pass
def SA_GotoGripperOpeningRelative_A(systemIndex, channelIndex, diff, speed): pass
def SA_GotoPositionAbsolute_A(systemIndex, channelIndex, position, holdTime): pass
def SA_GotoPositionRelative_A(systemIndex, channelIndex, diff, holdTime): pass
def SA_ScanMoveAbsolute_A(systemIndex, channelIndex, target, scanSpeed): pass
def SA_ScanMoveRelative_A(systemIndex, channelIndex, diff, scanSpeed): pass
def SA_StepMove_A(systemIndex, channelIndex, steps, amplitude, frequency): pass
def SA_Stop_A(systemIndex, channelIndex): pass
def SA_TriggerCommand_A(systemIndex, triggerIndex): pass

def SA_GetAngle_A(systemIndex, channelIndex): pass
def SA_GetCaptureBuffer_A(systemIndex, channelIndex, bufferIndex): pass
def SA_GetForce_A(systemIndex, channelIndex): pass
def SA_GetGripperOpening_A(systemIndex, channelIndex): pass
def SA_GetPosition_A(systemIndex, channelIndex): pass
def SA_GetStatus_A(systemIndex, channelIndex): pass
def SA_GetVoltageLevel_A(systemIndex, channelIndex): pass

def SA_DiscardPacket_A(systemIndex): pass
def SA_LookAtNextPacket_A(systemIndex, timeout, packet): pass
def SA_ReceiveNextPacket_A(systemIndex, timeout, packet): pass
def SA_CancelWaitForPacket_A(systemIndex): pass



