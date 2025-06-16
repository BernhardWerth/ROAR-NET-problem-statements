# SPDX-FileCopyrightText: 2025 Francesca Da Ros <francesca.daros@uniud.it>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Optional, Annotated, Any, Self
from pydantic import BaseModel, Field, model_validator, AliasChoices
from . instance_models import Instance, CostComponents
import math
import bisect
import click

class PatientVisit(BaseModel):
    """
    Represents a patient's visit with service times and related information.

    Attributes:

    Methods:
        _check_validity() -> Self:
            Validates that the start service time is less than the end service time and, if provided, that the arrival time is less than or equal to the start service time.
    """
    start_service_time: Annotated[int | float, Field(ge=0, alias=AliasChoices('start_service_time','start_time'))]
    end_service_time: Annotated[int | float, Field(ge=0, alias=AliasChoices('end_service_time', 'end_time'))]
    patient: str
    service: str
    arrival_at_patient: Annotated[int | float, Field(ge=0,  alias=AliasChoices('arrival_time','arrival_at_patient'))]
    departure_from_patient: Annotated[int | float, Field(ge=0,  alias=AliasChoices('departure_time','departure_from_patient'))]

    @model_validator(mode='after')
    def _check_validity(self) -> Self:
        assert self.start_service_time < self.end_service_time, f"Start service time for service {self.service} at patient {self.patient} is greater than end service time"
        assert self.arrival_at_patient <= self.start_service_time, f"Arrival at patient {self.patient} for service {self.service} is greater than start service time"
        assert self.end_service_time <= self.departure_from_patient, f"End service time for service {self.service} at patient {self.patient} is greater than departure time"
        return self
    
class DepotDeparture(BaseModel):
    """
    Represents a departure event from a depot.

    Attributes:
        departing_time (Annotated[int | float]): The time of departure from the depot. Must be a non-negative value.
        depot (str): The identifier or name of the depot.
    """
    departing_time: Annotated[int | float, Field(ge=0)]
    depot: str    

class DepotArrival(BaseModel):
    """
    Represents the arrival information at a depot.

    Attributes:
        arrival_time (int | float): The time of arrival at the depot. Must be greater than or equal to 0.
        depot (str): The name or identifier of the depot.
    """
    arrival_time: Annotated[int | float, Field(ge=0)]
    depot: str   

class CaregiverRoute(BaseModel):
    """
    Represents the route of a caregiver.

    Attributes:
        caregiver_id (str): The ID of the caregiver.
        locations (list[DepotDeparture | PatientVisit | DepotArrival]): List of locations in the caregiver's route.
        _visits (list[PatientVisit]): List of patient visits, excluded from serialization and representation.
        _full_route (bool): Indicates if the route is a full route (starting at a depot and ending at a depot), excluded from serialization and representation.

    Methods:
        _check_vallidity(): Validates the caregiver's route after model initialization. Ensures the route starts and ends at depots if it's a full route, checks the consistency of service times, and verifies the types of locations.
    """
    caregiver_id: str
    locations: Optional[list[DepotDeparture | PatientVisit | DepotArrival]] = None
    _visits: Annotated[list[PatientVisit], Field(exclude=True, repr=False)] = []
    _full_route: Annotated[bool, Field(exclude=True, repr=False)] = False

    @model_validator(mode='after')
    def _check_validity(self) -> Self:
        if self.locations:
            self._full_route = False
            if type(self.locations[0]) == DepotDeparture:
                assert type(self.locations[-1]) == DepotArrival, "First location is a depot but last location is not"
                self._full_route = True
            if self._full_route:                
                assert len(self.locations) > 2, f"Caregiver {self.caregiver_id} has a full route with no intermediate location"            
                self._visits = [self.locations[i] for i in range(1, len(self.locations) - 1)]
            else:
                self._visits = [l for l in self.locations]
            prev_time = 0 if not self._full_route else self.locations[0].departing_time
            for i, l in enumerate(self._visits):                
                assert type(l) == PatientVisit, f"Location {l} of caregiver {self.caregiver_id} (at step {i + 1 if self._full_route else i}) is not a patient location"
                assert l.start_service_time >= prev_time, f"Start service time of caregiver {self.caregiver_id} (at step {i + 1 if self._full_route else i}) {l.start_service_time} is not consistent with the previous one ({prev_time})"
                assert l.end_service_time  > l.start_service_time, f"End service time of caregiver {self.caregiver_id} (at step {i + 1 if self._full_route else i}) {l.end_service_time} is not greater than start service time {l.start_service_time}"
                prev_time = l.end_service_time
            if self._full_route:
                assert self.locations[-1].arrival_time >= prev_time, f"Arrival time at depot of caregiver {self.caregiver_id} {self.locations[-1].arrival_time} is not consistent with the previous end service time {prev_time}"
        return self    

class SolutionCostComponents(BaseModel):
    """
    Represents my cost components and weights
    """
    travel_time : Optional[int] = None
    total_tardiness : Optional[int] = None
    highest_tardiness :  Optional[int] = None
    total_waiting_time : Optional[int] = None
    total_extra_time : Optional[int] = None
    max_idle_time :  Optional[int] = None
    caregiver_preferences : Annotated[Optional[int], Field(alias=AliasChoices('preferences', 'caregiver_preferences'))] = None
    qualification : Optional[int] = None
    working_time : Optional[int] = None
    incompabilities : Optional[int] = None
    tw_max_dev_in_time : Optional[int] = None
    tw_max_dev_in_desired_time : Optional[int] = None
    workload_balance : Optional[int] = None
    max_waiting_time : Optional[int] = None

class Solution(BaseModel):
    """
    Represents a solution for a healthcare scheduling scenario.

    Attributes:
        instance (Optional[str]): The name of the instance this solution is for.
        routes (list[CaregiverRoute]): A list of routes for each caregiver.
        _normalized (bool): Internal flag indicating if the routes have been normalized.
    
    Methods:
        _check_validity() -> 'Solution':
            Validates the solution data after model creation.
        check_validity(instance: Instance):
            Checks the validity of the solution against the given instance.
        compute_costs(instance: Instance) -> float:
            Computes and returns the costs associated with the solution.
    """
    instance: Optional[Annotated[str, Field(min_length=1)]] = None
    routes: list[CaregiverRoute]
    cost_components: Optional[SolutionCostComponents] = None
    _normalized: Annotated[bool, Field(exclude=True, repr=False)] = False

    @model_validator(mode="before")
    @classmethod
    def validate_sd(cls, values : Any) -> Any:
        # this is just to avoid messy evaluations: making sure that the routes are ordered
        click.secho(f"About to perform prelimary checks while uploading", fg="green")
        for i, route in enumerate(values["routes"]):
            if "locations" not in route.keys():
                continue
            locations = route["locations"]
            ordered = sorted(locations, key=lambda x: x.get("arrival_time", x.get("start_time", x.get("start_service_time"))))
            values["routes"][i]["locations"] = ordered
        click.secho(f"End prelimary checks while uploading", fg="green")
        return values    

    @model_validator(mode='after')
    def _normalize_solution(self) -> 'Solution':
        click.secho(f"About to perform normalization of solution", fg="green")
        assert len(self.routes) == len(set(r.caregiver_id for r in self.routes)), "Some caregivers are repeated in the solution"
        self._normalized = True
        for r in self.routes:            
            if any(l.arrival_at_patient is not None for l in r._visits):
                self._normalized = False
                break
        click.secho(f"End normalization of solution", fg="green")
        return self
    
    def check_validity(self, instance : Instance):    
        visited_patients = {l.patient for r in self.routes for l in r._visits} 
        
        # check that the visited patients exist
        click.secho(f"Checking patients are existing patients", fg="green")
        for p in visited_patients:
            assert p in instance._patients.keys(), f"Patient {p} does not refer to the instance at hand."

        # check that all the patients are visited
        click.secho(f"Checking visited patients", fg="green")
        for p in  instance._patients.keys():
            if p not in visited_patients:
                click.secho(f"Patient {p} is not optional, but not scheduled", fg="red")

        # check that all services required by each patient are provided 
        click.secho(f"Checking that all services required by each patient are provided ", fg="green")
        for p in instance.patients:
            if p.id in visited_patients: # this is already checked before
                for s in p.required_services:
                    providing_caregivers = {r.caregiver_id for r in self.routes for l in r._visits if l.patient == p.id and l.service == s.service}
                    assert len(providing_caregivers) >= 1, f"Patient {p.id} requires service {s.service} which is not provided"
                    assert len(providing_caregivers) == 1, f"Patient {p.id} requires service {s.service} which is provided by more than one caregiver"

        click.secho(f"Checking that route normalization", fg="green")
        # normalize routes, by transforming them into full routes
        for r in self.routes:
            c = instance._caregivers[r.caregiver_id]
            if r._full_route:
                continue
            if r.locations is None or len(r.locations) == 0:
                click.secho(f"Route of caregiver {r.caregiver_id} is empty", fg="yellow")
                continue
            # search for the depot which is the first location of the caregiver
            depot_departure = instance._terminal_points[c.departing_point]        
            # search for the patient which is the first location of the caregiver
            first_service_index = instance._patients[r._visits[0].patient].distance_matrix_index
            travel_time = instance.distances[depot_departure.distance_matrix_index][first_service_index] 
            # compute the latest time the caregiver can depart to arrive at first patient
            r.locations.insert(0, DepotDeparture(departing_time=c.working_shift.start, depot=depot_departure.id))
            # compute the earliest time the caregiver arrive at the depot after the last patient (not that the arrival depot might differ from the departure one)
            depot_arrival = instance._terminal_points[c.arrival_point]
            last_patient = instance._patients[r._visits[-1].patient]
            travel_time = instance.distances[last_patient.distance_matrix_index][depot_arrival.distance_matrix_index]
            depot_arrival_time = r._visits[-1].end_service_time + travel_time
            r.locations.append(DepotArrival(arrival_time=depot_arrival_time, depot=depot_arrival.id))
            r._full_route = True

        click.secho(f"Checking distances normalizations", fg="green")
        # check that the times are consistent with the distances and normalize the arrival times
        for num_route,r in enumerate(self.routes):
            if r.locations is None or len(r.locations) == 0:
                continue # Don't throw anything as you should have already checked this
            for i in range(len(r._visits) - 1):
                start_index = instance._patients[r._visits[i].patient].distance_matrix_index
                end_index = instance._patients[r._visits[i + 1].patient].distance_matrix_index
                travel_time = instance.distances[start_index][end_index]
                assert r._visits[i + 1].start_service_time >= r._visits[i].end_service_time + travel_time, f"Route of caregiver {r.caregiver_id} is not consistent with the distances ({r.locations[i].end_service_time} + {travel_time} vs {r.locations[i + 1].start_service_time})"
                assert r._visits[i + 1].arrival_at_patient == r._visits[i].end_service_time + travel_time, f"Route of caregiver {r.caregiver_id} is not consistent with the distances ({r.locations[i].end_service_time} + {travel_time} vs {r.locations[i + 1].arrival_time})"
                assert r._visits[i + 1].start_service_time >= r._visits[i + 1].arrival_at_patient, f"Route of caregiver {r.caregiver_id} is not consistent with the arrival at patient"                
            # check the first location (i.e., depot)
            start_index = instance._terminal_points[r.locations[0].depot].distance_matrix_index
            end_index = instance._patients[r.locations[1].patient].distance_matrix_index
            travel_time = instance.distances[start_index][end_index]
            assert r.locations[1].start_service_time >= r.locations[0].departing_time + travel_time, f"Route of caregiver {r.caregiver_id} is not consistent with the distances from the depot ({r.locations[0].departing_time} + {travel_time} vs {r.locations[1].start_service_time})"
            assert r.locations[1].start_service_time >= r.locations[1].arrival_at_patient, f"Route of caregiver {r.caregiver_id} is not consistent with the arrival at patient"
            # check the last location (i.e., depot)
            start_index = instance._patients[r.locations[-2].patient].distance_matrix_index
            end_index = instance._terminal_points[r.locations[-1].depot].distance_matrix_index
            travel_time = instance.distances[start_index][end_index]
            assert r.locations[-1].arrival_time >= r.locations[-2].end_service_time + travel_time, f"Route of caregiver {r.caregiver_id} is not consistent with the distances to the depot ({r.locations[-2].end_service_time} + {travel_time} vs {r.locations[-1].arrival_time})"
            # check that the times are consistent with the service duration
            for num_visits,l in enumerate(r._visits):
                s = next(s for s in instance._patients[l.patient].required_services if s.service == l.service)
                assert l.end_service_time - l.start_service_time >= s._actual_duration, f"Route of caregiver {r.caregiver_id} at {l} is not consistent with the service durations"
            # check that the times are consistent with the working shift
            c = instance._caregivers[r.caregiver_id]
            assert c.working_shift is None or r.locations[0].departing_time >= c.working_shift.start, f"Route of caregiver {r.caregiver_id} is not consistent with his/her working shift (start shift: {c.working_shift.start}, departing_time: {r.locations[0].departing_time})"
        
        # check that for patients requiring sequential and simultaneous services, the services are provided correctly
        # i.e., you need to exclude those cases where you have indipendent services 
        for p in instance.patients:  
            if p.id not in visited_patients:
                continue          
            if p.synchronization is not None and p.synchronization.type != "independent": 
                caregivers = {l.service: l for r in self.routes for l in r._visits if l.patient == p.id}
                assert len(caregivers) == 2, f"Patient {p.id} requires double service but they are provided by the same caregiver"
                if p.synchronization.type == 'simultaneous':
                    assert caregivers[p.required_services[0].service].start_service_time == caregivers[p.required_services[0].service].start_service_time, f"Patient {p.id} requires simultaneous service but they are not provided simultaneously {caregivers[p.required_services[0].service].start_service_time} vs {caregivers[p.required_services[1].service].start_service_time}"
                else:
                    assert caregivers[p.required_services[0].service].start_service_time + p.synchronization.distance.min <= caregivers[p.required_services[1].service].start_service_time, f"Patient {p.id} requires sequential service ({p.required_services[0].service}, {p.required_services[1].service}) but the order is not respected (second service starting too early {caregivers[p.required_services[0].service].start_service_time} vs {caregivers[p.required_services[1].service].start_service_time} while min distance should be {p.synchronization.distance.min})"
                    assert caregivers[p.required_services[0].service].start_service_time + p.synchronization.distance.max >= caregivers[p.required_services[1].service].start_service_time, f"Patient {p.id} requires sequential service ({p.required_services[0].service}, {p.required_services[1].service}) but the order is not respected (second service starting too late {caregivers[p.required_services[0].service].start_service_time} vs {caregivers[p.required_services[1].service].start_service_time} while max distance should be {p.synchronization.distance.max})"
       
        # check that a patient is served after his/her time window starts
        for p in instance.patients:
            for r in self.routes:
                for l in r._visits:
                    if l.patient == p.id:
                        assert int(l.start_service_time) >= int(p.time_windows[0].start), f"Patient {p.id} is served ({l.start_service_time}) before the first time window starts {p.time_windows[0].start}"
        
        # check qualifications
        for r in self.routes:
            for l in r._visits:
                c = instance._caregivers[r.caregiver_id]
                if l.service not in c.abilities:
                    click.secho(f"Caregiver {r.caregiver_id} is performing a service ({l.service}) for which they are not abilitated.", fg="red")
        

        click.secho("Solution correcly validated", fg="green")
        return


    def compute_costs(self, instance : Instance) -> dict:
        click.secho("About to summurize the solution information", fg="green")
        
        visited_patients = {l.patient for r in self.routes for l in r._visits} 

        # compute distance travelled
        click.secho("*** TRAVELLED DISTANCES ***", fg="blue")
        travel_times = {c: 0 for c in instance._caregivers.keys()}
        for c in instance._caregivers.keys():
            travel_times[c] = 0
        distance_traveled = 0  
        for r in self.routes:
            distances_prints = [] 
            c = instance._caregivers[r.caregiver_id]
            start_index = instance._terminal_points[c.departing_point].distance_matrix_index
            for l in r._visits:
                end_index = None
                if l.patient in visited_patients:
                    end_index = instance._patients[l.patient].distance_matrix_index
                else: # FIXME: this is valid just because arrival and departing depot are the same
                    end_index = instance._terminal_points[instance._caregivers[r.caregiver_id].departing_point].distance_matrix_index
                tt = instance.distances[start_index][end_index]
                distances_prints.append(tt)
                distance_traveled += tt
                travel_times[c.id] += tt
                start_index = end_index
            end_index = instance._terminal_points[c.arrival_point].distance_matrix_index
            tt = instance.distances[start_index][end_index]
            distance_traveled += tt
            travel_times[c.id] += tt
            distances_prints.append(tt)
            click.secho(f"Distances of caregiver {r.caregiver_id} are: {distances_prints} (total: {travel_times[c.id]})", fg="blue")
        
        # compute tardiness
        click.secho("*** TARDINESS ***", fg="blue")
        tardiness = []
        for r in self.routes:
            for l in r._visits:
                p_id = l.patient
                p = instance._patients[p_id]
                starts = [tw.start for tw in p.time_windows] 
                idx = bisect.bisect_right(starts, l.start_service_time) - 1 # this give you the position where you should insert the service_start with respect the time of the starts of the windows. The -1 is so to have the index of the time window
                if instance.metadata.time_window_met == "at_service_start":
                    tardiness.append(max(0, l.start_service_time - p.time_windows[idx].end))
                    if l.start_service_time > p.time_windows[idx].end:
                        click.secho(f"Patient {p.id} visited by {r.caregiver_id} is tardy ({l.start_service_time - p.time_windows[idx].end})", fg="blue")
                else:
                    tardiness.append(max(0, l.end_service_time - p.time_windows[idx].end))
                    if l.end_service_time > p.time_windows[idx].end:
                        click.secho(f"Patient {p.id} visited by {r.caregiver_id} is tardy ({l.end_service_time - p.time_windows[idx].end})", fg="blue")

                        
        # compute waiting times
        click.secho("*** WAITING TIMES ***", fg="blue")
        waiting_time = []        
        for r in self.routes:
            for n_visit, l in enumerate(r._visits):
                if l.arrival_at_patient < l.start_service_time:
                    waiting_time.append(l.start_service_time - l.arrival_at_patient)
                    click.secho(f"Caregiver {r.caregiver_id} is waiting {l.start_service_time - l.arrival_at_patient} time units at patient {l.patient} (arrival: {l.arrival_at_patient}, start: {l.start_service_time}, end: {l.end_service_time})",fg="blue")
            
        # compute extratime
        click.secho("*** EXTRA TIME ***", fg="blue")
        extra_time = 0 
        for r in self.routes:
            c = instance._caregivers[r.caregiver_id]
            if c.working_shift is not None and r.locations is not None and len(r.locations) > 0: # one for each non-empty route
                if r.locations[-1].arrival_time > c.working_shift.end:
                    extra_time += r.locations[-1].arrival_time - c.working_shift.end
                    click.secho(f"Caregiver {c.id} is working extra time ({r.locations[-1].arrival_time - c.working_shift.end})", fg="blue")
        
        
        click.secho("*** INCOMPATIBILITIES ***", fg="blue")
        # number of incompatible caregivers
        incompatible_caregiver = 0
        for r in self.routes:
            for l in r._visits:
                # if the patient accounts for the concept of preferred_caregiver
                if instance._patients[l.patient].incompatible_caregivers is not None:
                    if r.caregiver_id in instance._patients[l.patient].incompatible_caregivers:
                        incompatible_caregiver += 1
                        click.secho(f"Patient {l.patient} is served by an incompatible caregiver ({r.caregiver_id})", fg="blue")
        
        # compute max idle time
        idle_times = {c: 0 for c in instance._caregivers.keys()}       
        for r in self.routes:
            c = instance._caregivers[r.caregiver_id]
            if c.working_shift is not None: 
                if r.locations is None or len(r.locations) == 0:
                    idle_times[c.id] += (c.working_shift.end - c.working_shift.start)
                else:
                    if r.locations[0].departing_time > c.working_shift.start:
                        idle_times[c.id] += r.locations[0].departing_time - c.working_shift.start
                    for i, l in enumerate(r._visits):
                        if l.arrival_at_patient < l.start_service_time:
                            idle_times[c.id] += l.start_service_time - l.arrival_at_patient
                    if r.locations[-1].arrival_time <= c.working_shift.end:
                        idle_times[c.id] += c.working_shift.end - r.locations[-1].arrival_time
        max_idle_time = max(idle_times.values())
        click.secho("*** IDLE TIMES ***", fg="blue")
        for c in idle_times.keys():
            if idle_times[c] >= max_idle_time:
                click.secho(f"Caregiver {c} has an idle time of {idle_times[c]}, which corresponds to the maximum.", fg = "blue")
            else:
                click.secho(f"Caregiver {c} has an idle time of {idle_times[c]}.", fg = "blue")

         # compute worload balance
        click.secho("*** SERVICE TIMES ***", fg="blue")
        # the workload of a caregiver is given by the service time and the travel time (you already calculated the travel time while calculating the travel distance)
        service_times = {c: 0 for c in instance._caregivers.keys()}
        for r in self.routes:
            for i, l in enumerate(r._visits):
                service_times[r.caregiver_id] += l.end_service_time - l.start_service_time
        for c in service_times.keys():
            click.secho(f"Caregiver {c} is at service for the following times: {service_times[c]}",fg="blue")
        
        total_workload = 0
        click.secho("*** WORKLOAD ***", fg="blue")
        for c in instance._caregivers.keys():
            total_workload += service_times[c] + travel_times[c]
            click.secho(f"Caregiver {c} has a workload of : {service_times[c] + travel_times[c]}",fg="blue")
        avg_workload = float(total_workload) / float(len(instance._caregivers))
        balance = 0
        for c in instance._caregivers.keys():
            balance += math.ceil(abs(service_times[c] + travel_times[c] - avg_workload))
                        
        # number of not respected preferences
        click.secho("*** PREFERENCES ***", fg="blue")
        preferred_caregiver = 0
        for r in self.routes:
            for l in r._visits: 
                if instance._patients[l.patient].preferred_caregivers is not None:
                    if r.caregiver_id not in instance._patients[l.patient].preferred_caregivers:
                        preferred_caregiver += 1
                        click.secho(f"Patient {l.patient} is served by a caregiver who is not one of their preferred ({r.caregiver_id})", fg="blue")
                
        def get_multiplier_cost(cost_component):
            if cost_component is None:
                return 0
            if cost_component == "HARD":
                return 1
            return cost_component
        
        tot = \
            get_multiplier_cost(instance.metadata.cost_components.total_tardiness) *  (sum(tardiness) if len(tardiness) > 0 else 0) +\
            get_multiplier_cost(instance.metadata.cost_components.highest_tardiness) *  (max(tardiness) if len(tardiness) > 0 else 0) +\
            get_multiplier_cost(instance.metadata.cost_components.travel_time) * distance_traveled +\
            get_multiplier_cost(instance.metadata.cost_components.total_extra_time) * extra_time +\
            get_multiplier_cost(instance.metadata.cost_components.max_idle_time) * max_idle_time +\
            get_multiplier_cost(instance.metadata.cost_components.total_waiting_time) * (sum(waiting_time) if len(waiting_time) > 0 else 0) +\
            get_multiplier_cost(instance.metadata.cost_components.max_waiting_time) * ( max(waiting_time) if len(waiting_time) > 0 else 0) +\
            get_multiplier_cost(instance.metadata.cost_components.working_time) * total_workload +\
            get_multiplier_cost(instance.metadata.cost_components.incompabilities) * incompatible_caregiver +\
            get_multiplier_cost(instance.metadata.cost_components.caregiver_preferences) * preferred_caregiver 

        cost_string_dict = {
            'total_tardiness': f"{get_multiplier_cost(instance.metadata.cost_components.total_tardiness) *  (sum(tardiness) if len(tardiness) > 0 else 0)}  ({get_multiplier_cost(instance.metadata.cost_components.total_tardiness)} x { sum(tardiness) if len(tardiness) > 0 else 0})",
            'max_tardiness': f"{get_multiplier_cost(instance.metadata.cost_components.highest_tardiness) *  (max(tardiness) if len(tardiness) > 0 else 0)}  ({get_multiplier_cost(instance.metadata.cost_components.highest_tardiness)} x { max(tardiness) if len(tardiness) > 0 else 0})",
            'traveled_distance': f"{get_multiplier_cost(instance.metadata.cost_components.travel_time) * distance_traveled}  ({get_multiplier_cost(instance.metadata.cost_components.travel_time)} x {distance_traveled})",
            'total_extra_time': f"{get_multiplier_cost(instance.metadata.cost_components.total_extra_time) * extra_time}  ({get_multiplier_cost(instance.metadata.cost_components.total_extra_time)} x {extra_time})",
            'max_idle_time': f"{get_multiplier_cost(instance.metadata.cost_components.max_idle_time) * max_idle_time}  ({get_multiplier_cost(instance.metadata.cost_components.max_idle_time)} x {max_idle_time})",
            'total_waiting_time': f"{get_multiplier_cost(instance.metadata.cost_components.total_waiting_time) * (sum(waiting_time) if len(waiting_time) > 0 else 0)}  ({get_multiplier_cost(instance.metadata.cost_components.total_waiting_time)} x {(sum(waiting_time) if len(waiting_time) > 0 else 0)})",
            'max_waiting_time': f"{get_multiplier_cost(instance.metadata.cost_components.max_waiting_time) * ( max(waiting_time) if len(waiting_time) > 0 else 0)}  ({get_multiplier_cost(instance.metadata.cost_components.max_waiting_time)} x {(max(waiting_time) if len(waiting_time) > 0 else 0,)})",
            'total_working_time': f"{get_multiplier_cost(instance.metadata.cost_components.working_time) * total_workload}  ({get_multiplier_cost(instance.metadata.cost_components.working_time)} x {total_workload})",
            'incompatible_caregiver': f"{get_multiplier_cost(instance.metadata.cost_components.incompabilities) * incompatible_caregiver}  ({get_multiplier_cost(instance.metadata.cost_components.incompabilities)} x {incompatible_caregiver})",  
            'preferred_caregiver': f"{get_multiplier_cost(instance.metadata.cost_components.caregiver_preferences) * preferred_caregiver}  ({get_multiplier_cost(instance.metadata.cost_components.caregiver_preferences)} x {preferred_caregiver})",
            'Total': f"{tot} (-)"
        }

        click.secho("Cost computed by validator are:", fg="green")

        max_key_length = max(len(key) for key in cost_string_dict)
        max_value_number_length = max(len(value.split()[0]) for value in cost_string_dict.values())

        for key, value in cost_string_dict.items():
            num, rest = value.split(maxsplit=1)
            formatted_line = f"{key.ljust(max_key_length + 5, '.')} {num.rjust(max_value_number_length)} ..... {rest}"
            click.secho(formatted_line, fg="blue")
        
        click.secho("About to check the costs of your solution:", fg="green")
        
        def checker(name, component_solution, component_validator, weight):
            if component_solution is not None:
                if component_solution == component_validator or component_solution == (get_multiplier_cost(weight)*component_validator):
                    click.secho(f"Cost related to {name} is consistent [ {component_solution } vs. {get_multiplier_cost(weight)*component_validator} ({get_multiplier_cost(weight)} x {component_validator}) ]", fg="blue")
                else:
                    click.secho(f"Cost related to {name} is not consistent [ {component_solution } vs. {get_multiplier_cost(weight)*component_validator} ({get_multiplier_cost(weight)} x {component_validator}) ]", fg="red")
        # get_multiplier_cost(instance.metadata.cost_components.total_tardiness) *  (sum(tardiness) if len(tardiness) > 0 else 0) +\
        checker("total_tardiness", self.cost_components.total_tardiness, (sum(tardiness) if len(tardiness) > 0 else 0), instance.metadata.cost_components.total_tardiness)
        # get_multiplier_cost(instance.metadata.cost_components.highest_tardiness) *  (max(tardiness) if len(tardiness) > 0 else 0) +\
        checker("max_tardiness", self.cost_components.highest_tardiness,  (max(tardiness) if len(tardiness) > 0 else 0), instance.metadata.cost_components.highest_tardiness)
        # get_multiplier_cost(instance.metadata.cost_components.travel_time) * distance_traveled +\
        checker("traveled_distance",self.cost_components.travel_time, distance_traveled, instance.metadata.cost_components.travel_time)
        # get_multiplier_cost(instance.metadata.cost_components.total_extra_time) * extra_time +\
        checker("total_extra_time", self.cost_components.total_extra_time, extra_time, instance.metadata.cost_components.total_extra_time)
        # get_multiplier_cost(instance.metadata.cost_components.max_idle_time) * max_idle_time +\
        checker("max_idle_time",self.cost_components.max_idle_time, max_idle_time, instance.metadata.cost_components.max_idle_time)
        # get_multiplier_cost(instance.metadata.cost_components.total_waiting_time) * (sum(waiting_time) if len(waiting_time) > 0 else 0) +\
        checker("total_waiting_time", self.cost_components.total_waiting_time,  (sum(waiting_time) if len(waiting_time) > 0 else 0), instance.metadata.cost_components.total_waiting_time )
        # get_multiplier_cost(instance.metadata.cost_components.max_waiting_time) * ( max(waiting_time) if len(waiting_time) > 0 else 0) +
        checker("max_waiting_time", self.cost_components.max_waiting_time, ( max(waiting_time) if len(waiting_time) > 0 else 0), instance.metadata.cost_components.max_waiting_time)
        # get_multiplier_cost(instance.metadata.cost_components.workload_balance) * balance +\
        checker("workload_balance", self.cost_components.workload_balance, balance, instance.metadata.cost_components.workload_balance)
        # get_multiplier_cost(instance.metadata.cost_components.working_time) * total_workload +\
        checker("total_workload", self.cost_components.working_time, total_workload, instance.metadata.cost_components.working_time)
        # get_multiplier_cost(instance.metadata.cost_components.incompabilities) * incompatible_caregiver +\
        checker("incompatible_caregiver", self.cost_components.incompabilities, incompatible_caregiver,instance.metadata.cost_components.incompabilities)
        # get_multiplier_cost(instance.metadata.cost_components.caregiver_preferences) * preferred_caregiver +\
        checker("preferred_caregiver", self.cost_components.caregiver_preferences, preferred_caregiver, instance.metadata.cost_components.caregiver_preferences)
        
        return cost_string_dict