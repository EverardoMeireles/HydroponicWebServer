@echo OFF

set pid=%1
start cmd /k py-spy top --pid %pid%
