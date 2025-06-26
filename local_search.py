from dataclasses import dataclass
from copy import copy
from circuit import Circuit, Module, Axis, Direction

class LocalSearch:
    @dataclass
    class PenaltyFeatures:
        overlap: int = 0
        connection_x: int = 0
        connection_y: int = 0

    @dataclass
    class UtilityFeatures:
        overlap: float = 0.
        connection_x: float = 0.
        connection_y: float = 0.

    Features = PenaltyFeatures | UtilityFeatures

    def __init__(self, circuit: Circuit):
        self.circuit = circuit

        self.penalties = self._init_modules_pairs_dict(LocalSearch.PenaltyFeatures())
        self.penalties_weight = self.circuit.get_avg_module_area() / 10.0

    def _init_modules_pairs_dict(self, default_value: Features) -> dict[tuple[Module, Module], Features]:
        result = {}

        for i in range(self.circuit.num_modules-1):
            module1 = self.circuit.modules[i]
            for j in range(i+1, self.circuit.num_modules):
                module2 = self.circuit.modules[j]

                result[(module1, module2)] = copy(default_value)

        return result

    def objective_func(self) -> int:
        result = self.circuit.get_bounding_boxes_total()

        for i in range(self.circuit.num_modules-1):
            module1 = self.circuit.modules[i]
            for j in range(i+1, self.circuit.num_modules):
                module2 = self.circuit.modules[j]

                result += self.circuit.get_modules_overlap_area(module1, module2)

        return result

    def augmented_objective_func(self) -> float:
        result = self.circuit.get_bounding_boxes_total()

        for i in range(self.circuit.num_modules-1):
            module1 = self.circuit.modules[i]
            for j in range(i+1, self.circuit.num_modules):
                module2 = self.circuit.modules[j]
                pair_penalties = self.penalties[(module1, module2)]

                overlap_area = self.circuit.get_modules_overlap_area(module1, module2)
                overlap_penalty = int(overlap_area > 0) * pair_penalties.overlap

                connection_penalty = 0

                if (module1, module2) in self.circuit.connected_modules_pairs:
                    distance = self.circuit.get_modules_distance_per_axis(module1, module2)

                    connection_penalty_x = int(distance.dx > 0) * pair_penalties.connection_x
                    connection_penalty_y = int(distance.dy > 0) * pair_penalties.connection_y

                    connection_penalty = connection_penalty_x + connection_penalty_y

                result += overlap_area + self.penalties_weight * (overlap_penalty + connection_penalty)

        return result

    def update_penalties(self):
        utilities = self._init_modules_pairs_dict(LocalSearch.UtilityFeatures())

        any_overlap = False
        max_utility = 0.

        for i in range(self.circuit.num_modules-1):
            module1 = self.circuit.modules[i]
            for j in range(i+1, self.circuit.num_modules):
                module2 = self.circuit.modules[j]
                pair = (module1, module2)

                overlap_area = self.circuit.get_modules_overlap_area(module1, module2)

                if overlap_area > 0:
                    overlap_cost = overlap_area + module1.area + module2.area
                    utilities[pair].overlap = overlap_cost / (1 + self.penalties[pair].overlap)

                    max_utility = max(max_utility, utilities[pair].overlap)
                    any_overlap = True

                if pair in self.circuit.connected_modules_pairs:
                    distance = self.circuit.get_modules_distance_per_axis(module1, module2)

                    if distance.dx > 0:
                        utilities[pair].connection_x = distance.dx / (1 + self.penalties[pair].connection_x)
                        max_utility = max(max_utility, utilities[pair].connection_x)

                    if distance.dy > 0:
                        utilities[pair].connection_y = distance.dy / (1 + self.penalties[pair].connection_y)
                        max_utility = max(max_utility, utilities[pair].connection_y)

        if not any_overlap:
            # Reset penalties
            self.penalties = self._init_modules_pairs_dict(LocalSearch.PenaltyFeatures())

        for i in range(self.circuit.num_modules-1):
            module1 = self.circuit.modules[i]
            for j in range(i+1, self.circuit.num_modules):
                module2 = self.circuit.modules[j]
                pair = (module1, module2)

                self.penalties[pair].overlap += int(utilities[pair].overlap == max_utility)
                self.penalties[pair].connection_x += int(utilities[pair].connection_x == max_utility)
                self.penalties[pair].connection_y += int(utilities[pair].connection_y == max_utility)

    def to_local_optimum_placement(self):
        actions_funcs = {}
        for module in self.circuit.modules:
            actions_funcs[module] = []

            for axis in Axis:
                actions_funcs[module].append(lambda module=module, axis=axis: self.circuit.reflect_module(module, axis))

            for direction in Direction:
                actions_funcs[module].append(lambda module=module, direction=direction: self.circuit.translate_module_until_collision(module, direction))

            for angle in (90, 180, 270):
                actions_funcs[module].append(lambda module=module, angle=angle: self.circuit.rotate_module_cw(module, angle))

        prev_best_value = float("inf")
        active_modules = self.circuit.modules

        while len(active_modules) > 0:
            best_value = float("inf")
            
            best_action_func = None
            best_action_module = None

            for module in active_modules:
                pin = self.circuit.modules_pins[module]

                module0, pin0 = copy(module), copy(pin)

                for action_func in actions_funcs[module]:
                    action_func()

                    self.circuit.DEBUG_sanity_check()

                    if (value := self.augmented_objective_func()) < best_value:
                        best_action_func = action_func
                        best_action_module = module

                        best_value = value

                    # Backtrack
                    module.copy(module0)
                    pin.copy(pin0)

            if best_value < prev_best_value:
                best_action_func()

                # Check only the modules that have been impacted by the best move
                active_modules = []
                for other_module in self.circuit.modules:
                    # The module itself is going to be readded, since it has positive overlap
                    if (best_action_module, other_module) in self.circuit.connected_modules_pairs or \
                    self.circuit.get_modules_overlap_area(best_action_module, other_module) > 0:
                        active_modules.append(other_module)
            else:
                break

            prev_best_value = best_value

    def to_optimal_placement(self, max_num_iterations: int = 1000, max_stagnation: int = 30, verbose: bool = True):
        assert max_num_iterations > 0

        optimal_circuit = copy(self.circuit)
        optimal_value = float("inf")

        if verbose:
            print("[ITER] VALUE    | FEASIBILITY")
            print(f"{'-' * 40}")

        stagnation_count = 0

        for i in range(1, max_num_iterations+1):
            self.to_local_optimum_placement()

            value = self.objective_func()

            if value < optimal_value:
                optimal_circuit.copy(self.circuit)
                optimal_value = value

                stagnation_count = 0
            else:
                stagnation_count += 1
                if stagnation_count == max_stagnation:
                    break

            if verbose:
                feasible_str = "FEASIBLE" if self.circuit.is_feasible() else "NOT FEASIBLE"
                print(f"[{i:4}] {optimal_value:8} | {feasible_str}")

            self.update_penalties()

        self.circuit.copy(optimal_circuit)
