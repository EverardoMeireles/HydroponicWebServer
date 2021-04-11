class Schedule:
    def __init__(self, serial_number, instruction, to_delete, type, timestamp):
        self.serial_number = serial_number
        self.instruction = instruction
        self.to_delete = to_delete
        self.type = type
        self.timestamp = timestamp