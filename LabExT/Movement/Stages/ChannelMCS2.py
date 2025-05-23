try:
    import smaract.ctl as ctl
    MCS_LOADED = True
except (ImportError, OSError):
    ctl = None
    MCS_LOADED = False

class ChannelMCS2:
    """Implementation of one SmarAct synchronous channel. One channel represents one axis.

    Attributes
    ----------
    name : str
        Human-readable description of the channel
    _status : int
        Current channel status
    _sensor : int
        Channel sensor
    _position : int
        Current absolute position in micrometer
    _speed : float
        Speed setting of channel in micrometers/seconds
    _acceleration : float
        Acceleration setting of channel in micrometers/seconds^2
    movement_mode
        Movement type of the channel

    Methods
    -------
    move(value, mode):
        Moves the channel with the specified movement type by the value 'value'
    find_reference_mark():
        Finds reference mark of channel
    """
    LINEAR_SENSORS = {
        "SL...S1SS",
        "SL...S1ME",
        "SL...S1SC1",
        "SL...T1SS",
        "SL...D1SS",
        "SL...D1SC2",
        "SL...D1SC1",
        "SL...D1ME",
        "CT002/AT002"
    } if MCS_LOADED else {}

    def __init__(self, stage, index, name='Channel') -> None:
        """Constructs all necessary attributes of the channel object.

        Parameters
        ----------
        stage : Stage
            stage object, to which this channel belongs
        index : int
            Channel index
        name : str
            (Optional) Human-readable description of channel
        """
        self.name = name
        self._stage = stage
        self._handle = index
        self._status = None
        if MCS_LOADED:
            self._movement_mode = ctl.MoveMode.CL_RELATIVE
        else:
            self._movement_mode = None
        self._position = None
        self._sensor = None
        self._speed = 0
        self._acceleration = 0

    @property
    def status(self) -> int:
        """Returns the current channel status code. This code can have multiple status strings encoded. """
        self._status = ctl.GetProperty_i32(self._stage.handle, self._handle, ctl.Property.CHANNEL_STATE)
        return self._status

    @property
    def humanized_status(self) -> list:
        """Translate current status to list of strings."""
        status_code = self.status
        states = []
        for state in ctl.ChannelState:
            if status_code & state.value:
                states.append(state.name)
        if not states:
            return [f'Unknown status code: {status_code}']
        return states

    @property
    def sensor(self) -> str:
        """Returns channel sensor type as string."""
        self._sensor = ctl.GetProperty_s(self._stage.handle, self._handle, ctl.Property.POSITIONER_TYPE_NAME)
        return self._sensor

    @property
    def is_sensor_linear(self) -> bool:
        """Returns a decision whether the sensor is linear."""
        return self.sensor in self.LINEAR_SENSORS

    @property
    def position(self) -> float:
        """Returns current position of channel in micrometers."""
        position_pm = ctl.GetProperty_i64(self._stage.handle, self._handle, ctl.Property.POSITION)
        self._position = self._to_micrometer(position_pm)
        return self._position

    @property
    def speed(self) -> float:
        """Returns speed setting og channel in micrometers/seconds."""
        velocity_pmps = ctl.GetProperty_i64(self._stage.handle, self._handle, ctl.Property.MOVE_VELOCITY)
        self._speed = self._to_micrometer(velocity_pmps)
        return self._speed

    @speed.setter
    def speed(self, umps: float) -> None:
        """Sets speed of channel given in micrometers/seconds."""
        velocity_pmps = self._to_picometer(umps)
        ctl.SetProperty_i64(self._stage.handle, self._handle, ctl.Property.MOVE_VELOCITY, velocity_pmps)
        self._speed = umps

    @property
    def acceleration(self) -> float:
        """Returns acceleration of channel in micrometers/seconds^2."""
        acceleration_pmps2 = ctl.GetProperty_i64(self._stage.handle, self._handle, ctl.Property.MOVE_ACCELERATION)
        self._acceleration = self._to_micrometer(acceleration_pmps2)
        return self._acceleration

    @acceleration.setter
    def acceleration(self, umps2: float) -> None:
        """Sets the acceleration of channel given in micrometers/seconds^2."""
        acceleration_pmps2 = self._to_picometer(umps2)
        ctl.SetProperty_i64(self._stage.handle, self._handle, ctl.Property.MOVE_ACCELERATION, acceleration_pmps2)
        self._acceleration = umps2

    @property
    def movement_mode(self):
        """Returns movement mode of channel as MoveMode enum."""
        return self._movement_mode

    @movement_mode.setter
    def movement_mode(self, mode) -> None:
        """Sets the movement mode of channel as MoveMode enum."""
        if not isinstance(mode, ctl.MoveMode):
            raise ValueError(f'Invalid movement mode {mode}')
        ctl.SetProperty_i32(self._stage.handle, self._handle, ctl.Property.MOVE_MODE, mode)
        self._movement_mode = mode

    # Channel Control

    def stop(self) -> None:
        """Stops all movement of this channel."""
        ctl.Stop(self._stage.handle, self._handle)

    # Movement

    def move(self, value: float, mode) -> None:
        """Moves the channel with the specified movement type by the value 'value'.
        Parameters
        ----------
        value : float
            Channel movement measured in micrometers
        mode : ctl.MoveMode
            Channel movement type (e.g. ctl.MoveMode.CL_ABSOLUTE)
        """
        self.movement_mode = mode
        ctl.Move(self._stage.handle, self._handle, self._to_picometer(value))

    def find_reference_mark(self):
        raise NotImplementedError

    # Helper functions

    @staticmethod
    def _to_micrometer(picometer: int) -> float:
        return picometer * 1e-6

    @staticmethod
    def _to_picometer(micrometer: float) -> int:
        return int(micrometer * 1e6)