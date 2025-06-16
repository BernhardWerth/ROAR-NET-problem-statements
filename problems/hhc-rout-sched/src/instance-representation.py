# SPDX-FileCopyrightText: 2025 Francesca Da Ros <francesca.daros@uniud.it>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import sys
import json
import logging
from dataclasses import dataclass
from typing import TextIO, Optional, Union

import argparse
import logging

@dataclass
class Service:
    service : str
    duration : int
    type : Optional[str] = None

@dataclass
class TimeWindow:
    start : int
    end : int

@dataclass
class Synchronization:
    type : str

@dataclass
class Patient:
    id : str
    required_services : list[Service]
    distance_matrix_index : int
    time_windows : list[TimeWindow]
    location : tuple[Union[int, float], Union[int, float]]
    synchronization : Optional[Synchronization] = None

@dataclass
class Employee:
    id : str
    abilities : list[str]
    departing_point : str
    arrival_point : str
    working_shift : TimeWindow

@dataclass
class TerminalPoint:
    id : str
    distance_matrix_index : int
    location : tuple[Union[int, float], Union[int, float]]

class Problem():
    def __init__(self, patients:dict, employees:dict, terminal_points:dict, services:dict, distancees:list[list[int]],
                w_tardiness:int, w_idle_time:int, w_travel_time:int):
        self._patients = patients 
        self._employees = employees
        self._terminal_points = terminal_points
        self._services = services
        self.distances = distancees
        self.w_tardiness = w_tardiness
        self.w_idle_time = w_idle_time
        self.w_travel_time = w_travel_time


        # redundant data structure 
        self._patient_services = self.rds_patient_services()
        self._service_providers = self.rds_service_providers()
    
    @classmethod
    def from_textio(cls, f: TextIO) -> Problem:
        """
        Create a problem from a text I/O source `f`
        """
        instance = json.load(f)

        patients = dict()
        for p in instance["patients"]:
            patients[p["id"]]  = Patient(
                id=p["id"],
                required_services=[Service(service=service["service"], duration=service["duration"]) for service in p["required_services"]],
                time_windows=[TimeWindow(start=tw["start"], end=tw["end"]) for tw in p["time_windows"]],
                distance_matrix_index=p["distance_matrix_index"],
                location=(float(p["location"][0]), float(p["location"][1]))
            )

        employees = dict()
        for e in instance["caregivers"]:
            employees[e["id"]] = Employee(
                id=e["id"],
                working_shift=TimeWindow(start=e["working_shift"]["start"], end=e["working_shift"]["end"]),
                departing_point=e["departing_point"],
                arrival_point=e["arrival_point"],
                abilities=e["abilities"]
            )
        
        terminal_points = dict()
        for tp in instance["terminal_points"]:
            terminal_points[tp["id"]] = TerminalPoint(
                id=tp["id"],
                distance_matrix_index=tp["distance_matrix_index"],
                location=(float(tp["location"][0]),float(tp["location"][1]))
            )

        services = dict()
        for srv in instance["services"]:
            services[srv["id"]] = Service(
                service=srv["id"],
                type=srv["type"],
                duration=srv["default_duration"]
            )

        return cls(patients, employees, terminal_points, services, instance["distances"], instance["metadata"]["cost_components"]["total_tardiness"] , instance["metadata"]["cost_components"]["max_idle_time"], instance["metadata"]["cost_components"]["travel_time"])
    
    def __str__(self):
        return (f"Problem with {self.patients()} total patients, {self.employees()} employees, {self.services()} services type ({self.services_to_perform()} to perform).")
    

    def rds_patient_services(self) -> dict[str, dict[str, int]]:
        logging.debug("Updating redundant data structure: patient_services")
        patient_services: dict[str, dict[str, int]] = dict()
        for p in self._patients:
            patient = self._patients[p]
            patient_services[p] = dict()
            for srv in patient.required_services:
                patient_services[p][srv.service] = srv.duration
        return patient_services

    def rds_service_providers(self) -> dict[str,set[str]]:
        logging.debug("Updating redundant data structure: rds_service_providers")
        service_to_employee:dict[str,set[str]] = dict()
        for e in self._employees.keys():
            for a in self._employees[e].abilities:
                if a in service_to_employee:
                    service_to_employee[a].add(e)
                else:
                    service_to_employee[a] = set()
                    service_to_employee[a].add(e)
        return service_to_employee
    
    # getters
    def patients(self) -> int:
        "Number of patients"
        return len(self._patients)
    
    def single_service_patients(self) -> int:
        "Number of patients requiring single service"
        tot = 0
        for p in self._patients:
            if len(self._patients[p].required_services) == 1:
                tot += 1
        return tot

    def double_service_patients(self) -> int:
        "Number of patients requiring two services"
        tot = 0
        for p in self._patients:
            if len(self._patients[p].required_services) == 2:
                tot += 1
        return tot

    def services(self) -> int:
        "Number of service classes."
        return len(self._services)
    
    def services_to_perform(self) -> int:
        "Number of services to perform"
        tot = 0
        for p in self._patients:
            tot += len(self._patients[p].required_services)
        return tot

    def employees(self) -> int:
        "Number of employees (i.e., caregivers)"
        return len(self._employees)

    def locations(self) -> int:
        "Number of locations (i.e., nodes)"
        return len(self.distances)
    
    def terminal_points(self) -> int:
        "Number of terminal points"
        return len(self._terminal_points)

    def ability(self, e:int, s:str) -> bool:
        "Return True if employee e has skill s"
        employee = self._employees.get(e)
        if not employee:
            raise ValueError(f"Employee with id {e} not found.")
        return s in employee.abilities

    def is_single_service(self, p:str) -> bool:
        "Return True if patient p requires only one service."
        return len(self._patients[p].required_services) == 1
    
    def is_double_service(self, p:str) -> bool:
        "Return True if patient p requires two services."
        return len(self._patients[p].required_services) == 2
    
    def duration(self, s:str, p:str) -> int:
        "Return the duration of service s when performed at patient p."
        patient = self._patient_services.get(p)
        if not patient:
            raise ValueError(f"Patient with id {p} not found. Patients are: {list(self._patients.keys())}")
        service = patient.get(s)
        if service:
            return service
        raise ValueError(f"Service with id {s} not found. Services for patient {p} are: {list(self._patient_services[p])}")

    def employee_abilities(self, e:str) -> int:
        "Return the number of abilities of employee e"
        employee = self._employees.get(e)
        if not employee:
            raise ValueError(f"Employee with id {e} not found.")
        return len(employee.abilities)
    
    def start_time_window(self, p:str) -> int:
        "Return the start time of patient p timewindow"
        patient = self._patients.get(p)
        if not patient:
            raise ValueError(f"Patient with id {p} not found.")
        return patient.time_windows[0].start
    
    def end_time_window(self, p:str) -> int:
        "Return the end time of patient p timewindow"
        patient = self._patients.get(p)
        if not patient:
            raise ValueError(f"Patient with id {p} not found.")
        return patient.time_windows[0].end
    
    def first_service(self, p:str) -> str:
        "Return the first service required by patient p"
        patient = self._patients.get(p)
        if not patient:
            raise ValueError(f"Patient with id {p} not found.")
        return patient.required_services[0].service
    
    def employee_departure_matrix_index(self, e:str) -> int:
        employee = self._employees.get(e)
        if not employee:
            raise ValueError(f"Employee with id {e} not found.")
        terminal_point = self._terminal_points.get(employee.departing_point)
        if not terminal_point:
            raise ValueError(f"Terminal point with id {employee.departing_point} not found.")
        return terminal_point.distance_matrix_index
    
    def employee_arrival_matrix_index(self, e:str) -> int:
        employee = self._employees.get(e)
        if not employee:
            raise ValueError(f"Employee with id {e} not found.")
        terminal_point = self._terminal_points.get(employee.arrival_point)
        if not terminal_point:
            raise ValueError(f"Terminal point with id {employee.arrival_point} not found.")
        return terminal_point.distance_matrix_index
    
    def patient_matrix_index(self, p:str) -> int:
        patient = self._patients.get(p)
        if not patient:
            raise ValueError(f"Patient with id {p} not found.")
        return patient.distance_matrix_index
    
    def start_shift(self, e:str) -> int:
        employee = self._employees.get(e)
        if not employee:
            raise ValueError(f"Employee with id {e} not found.")
        return employee.working_shift.start
    
    def end_shift(self, e:str) -> int:
        employee = self._employees.get(e)
        if not employee:
            raise ValueError(f"Employee with id {e} not found.")
        return employee.working_shift.end 
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-file', type=argparse.FileType('r'), required=True)
    parser.add_argument('--log-file', type=argparse.FileType('w'), default=sys.stderr)
    parser.add_argument('--log-level',
                        choices=['critical', 'error', 'warning', 'info', 'debug'],
                        default='info')
    args = parser.parse_args()

    logging.basicConfig(stream=args.log_file,
                        level=args.log_level.upper(),
                        format="%(levelname)s; %(asctime)s; %(message)s")
    
    p = Problem.from_textio(args.input_file)
    logging.info(p)