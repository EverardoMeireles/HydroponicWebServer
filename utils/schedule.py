class Schedule:
    def __init__(self, serial_number, instruction, to_delete, postpone, type, timestamp, re_insertion_time_seconds):
        self.serial_number = serial_number
        self.instruction = instruction
        self.to_delete = to_delete
        self.postponed = postpone
        self.type = type
        self.timestamp = timestamp
        self.re_insertion_time_seconds = re_insertion_time_seconds
