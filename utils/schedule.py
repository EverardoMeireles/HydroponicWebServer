class Schedule:
    def __init__(self, serial_number, instruction, to_delete, postpone, type, timestamp):
        self.serial_number = serial_number
        self.instruction = instruction
        self.to_delete = to_delete
        self.postponed = postpone
        self.type = type
        self.timestamp = timestamp
