from math import radians

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

import common


class AirHauler(object):
    def __init__(self):
        self.airports = common.load_airports()
        self.aircraft = common.load_aircraft()
        self.jobs = common.load_jobs()

    def calculate_jobs(self):
        print("Create dataset from 'Jobs.xlsx'.")
        data = self.create_data_model()

        print("Create the routing index manager.")
        manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_planes'], data['base'])

        print("Create Routing Model.")
        routing = pywrapcp.RoutingModel(manager)

        print("Create and register a transit callback.")

        def distance_callback(from_index, to_index):
            """Returns the distance between the two nodes."""
            # Convert from routing variable Index to distance matrix NodeIndex.
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['distance_matrix'][from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)

        print("Define cost of each arc.")
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        print("Add Distance constraint.")
        dimension_name = 'Distance'
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            70000,  # vehicle maximum travel distance
            True,  # start cumul to zero
            dimension_name)
        distance_dimension = routing.GetDimensionOrDie(dimension_name)
        distance_dimension.SetGlobalSpanCostCoefficient(100)

        print("Define Transportation Requests.")
        for request in data['pickups_deliveries']:
            pickup_index = manager.NodeToIndex(request[0])
            delivery_index = manager.NodeToIndex(request[1])
            routing.AddPickupAndDelivery(pickup_index, delivery_index)
            routing.solver().Add(
                routing.VehicleVar(pickup_index) == routing.VehicleVar(
                    delivery_index))
            routing.solver().Add(
                distance_dimension.CumulVar(pickup_index) <=
                distance_dimension.CumulVar(delivery_index))

        def demand_callback(from_index, to_index):
            """Returns the demand between the two nodes."""
            # Convert from routing variable Index to demand matrix NodeIndex.
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)

            if from_node == to_node:
                return 0

            from_icao = self.locations[from_node]
            to_icao = self.locations[to_node]

            df = self.jobs[(self.jobs.fromIcao == from_icao) &
                           (self.jobs.toIcao == to_icao)]

            return df['quantity'].iloc[1]

        demand_callback_index = routing.RegisterTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            [500],  # vehicle maximum capacities
            True,  # start cumul to zero
            'Capacity')

        print("Setting first solution heuristic.")
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)

        print("Solve the problem.")
        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            self.print_solution(data, manager, routing, solution)

    def print_solution(self, data, manager, routing, solution):
        """Prints solution on console."""
        total_distance = 0
        total_load = 0
        for vehicle_id in range(data['num_planes']):
            index = routing.Start(vehicle_id)
            plan_output = 'Route for aircraft {}:\n'.format(vehicle_id)
            route_distance = 0
            route_load = 0
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route_load += data['demands'][node_index]
                plan_output += ' {0} Load({1}) -> '.format(self.locations[manager.IndexToNode(index)], route_load)
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id)
            plan_output += ' {0} Load({1})\n'.format(self.locations[manager.IndexToNode(index)],
                                                     route_load)
            plan_output += 'Distance of the route: {}nm\n'.format(route_distance)
            plan_output += 'Load of the route: {}\n'.format(route_load)
            print(plan_output)
            total_distance += route_distance
            total_load += route_load
        print('Total Distance of all routes: {}nm'.format(total_distance))
        print('Total load of all routes: {}'.format(total_load))

    def create_data_model(self):
        """Stores the data for the problem."""
        data = {}

        aircraft_icao = self.aircraft['Location'][0]
        pickups_deliveries = []
        self.locations = []
        for job in self.jobs.iterrows():
            selectedJob = job[1]
            if selectedJob['toIcao'] not in self.locations:
                self.locations.append(selectedJob['toIcao'])

            if selectedJob['fromIcao'] not in self.locations:
                self.locations.append(selectedJob['fromIcao'])

            if selectedJob['fromIcao'] != aircraft_icao and selectedJob['toIcao'] != aircraft_icao:
                pickups_deliveries.append(
                    [self.locations.index(selectedJob['fromIcao']), self.locations.index(selectedJob['toIcao'])])

        distance_matrix = []
        for icao1 in self.locations:
            distances = []
            for icao2 in self.locations:
                distances.append(self.get_distance(icao1, icao2))

            distance_matrix.append(distances)

        data['pickups_deliveries'] = pickups_deliveries
        data['distance_matrix'] = distance_matrix
        data['num_planes'] = 1
        data['base'] = self.locations.index(aircraft_icao)
        return data

    def get_distance(self, from_icao, to_icao):
        if len(from_icao) == 3:
            if len(self.airports[self.airports.ident == "K" + from_icao][
                       ['latitude_deg', 'longitude_deg']]['latitude_deg']) > 0:
                from_icao = "K" + from_icao
            elif len(self.airports[self.airports.ident == "C" + from_icao][
                         ['latitude_deg', 'longitude_deg']]['latitude_deg']) > 0:
                from_icao = "C" + from_icao

        if len(to_icao) == 3:
            if len(self.airports[self.airports.ident == "K" + to_icao][['latitude_deg', 'longitude_deg']][
                       'latitude_deg']) > 0:
                to_icao = "K" + to_icao
            elif len(self.airports[self.airports.ident == "C" + to_icao][
                         ['latitude_deg', 'longitude_deg']]['latitude_deg']) > 0:
                to_icao = "C" + to_icao

        if len(self.airports[self.airports.ident == from_icao][['latitude_deg', 'longitude_deg']][
                   'latitude_deg']) == 0 or len(
                self.airports[self.airports.ident == to_icao][['latitude_deg', 'longitude_deg']]['latitude_deg']) == 0:
            return 99999

        lat1, lon1 = [radians(x) for x in
                      self.airports[self.airports.ident == from_icao][['latitude_deg', 'longitude_deg']].iloc[0]]
        lat2, lon2 = [radians(x) for x in
                      self.airports[self.airports.ident == to_icao][['latitude_deg', 'longitude_deg']].iloc[0]]
        return common.get_distance(lat1, lon1, lat2, lon2)
