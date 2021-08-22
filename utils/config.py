import configparser

config = configparser.ConfigParser()
config.read("config.ini")

room_map = [["Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z"],
            ["Z", "G", "Z", "Z", "G", "Z", "Z", "Z", "G", "Z"],
            ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
            ["Z", "Z", "G", "G", "G", "Z", "Z", "G", "G", "Z"],
            ["Z", "Z", "Z", "G", "Z", "Z", "G", "Z", "Z", "Z"],
            ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
            ["Z", "Z", "Z", "G", "G", "Z", "G", "Z", "G", "Z"],
            ["Z", "Z", "Z", "G", "Z", "Z", "G", "Z", "Z", "Z"],
            ["Z", "G", "G", "G", "G", "G", "G", "G", "G", "Z"],
            ["Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z", "Z"]]
