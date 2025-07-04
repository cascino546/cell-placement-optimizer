from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from copy import deepcopy
from helpers import debug, Rectangle, get_rectangles_overlap_area

class Pin:
    # We are going to consider them to be constant in size
    width: int = 1
    height: int = 1

    def __init__(self, dx: int, dy: int):
        assert dx >= 0
        assert dy >= 0

        self.dx = dx
        self.dy = dy

    def __str__(self) -> str:
        return f"Pin({self.dx}, {self.dy})"

    def copy(self, other: Pin):
        self.dx = other.dx
        self.dy = other.dy

class Module:
    def __init__(self, position: tuple[int, int], size: tuple[int, int]):
        assert all(coord >= 0 for coord in position)
        assert all(length >= 0 for length in size)

        self.x, self.y = position
        self.width, self.height = size

    @property
    def area(self) -> int:
        return self.width * self.height      

    def copy(self, other: Module):
        self.x = other.x
        self.y = other.y

        self.width = other.width
        self.height = other.height

    def __str__(self) -> str:
        return f"Module(({self.x}, {self.y}), ({self.width}, {self.height}))"

class Netlist:
    def __init__(self, pins: list[Pin]):
        self.pins = pins

    def __len__(self) -> int:
        return len(self.pins)

    def __getitem__(self, idx: int) -> int:
        return self.pins[idx]

    def __iter__(self) -> Pin:
        for pin in self.pins:
            yield pin

    def __str__(self) -> str:
        return "{" + " ".join([str(pin) for pin in self.pins]) + "}"

class Axis(Enum):
    X = 1
    Y = 2

class Direction(Enum):
    NORTH = 1
    EAST = 2
    SOUTH = 3
    WEST = 4

    def is_vertical(self):
        return self == Direction.NORTH or self == Direction.SOUTH

    def is_horizontal(self):
        return self == Direction.EAST or self == Direction.WEST
    
    # By convention, Y-axis increases up and X-axis right
    def is_positive(self):
        return self == Direction.NORTH or self == Direction.EAST

    # By convention, Y-axis decreases down and X-axis left
    def is_negative(self):
        return self == Direction.SOUTH or self == Direction.WEST

@dataclass
class DistancePerAxis:
    dx: int
    dy: int

class Circuit:
    def __init__(self, width: int, height: int):
        assert width > 0
        assert height > 0

        self.width = width
        self.height = height

        self.module_to_pins = {}
        self.pin_to_module = {}

        self.netlists = []
        self.modules = []
        self.connected_modules_pairs = set()

    @property
    def num_modules(self):
        assert len(self.modules) == len(self.module_to_pins)

        return len(self.modules)
    
    def __str__(self) -> str:
        separator = f"{'-' * 40}\n"

        string = f"\nCircuit({self.width}, {self.height})\n\n"

        string += "MODULES\n"
        string += separator
        
        for module, pins in self.module_to_pins.items():
            string += f"{str(module)} <--> "
            string += "[ "
            for pin in pins:
                string += f"{str(pin)} "
            string += "]\n"
        
        string += "NETLISTS\n"
        string += separator

        for netlist in self.netlists:
            for pin in netlist:
                module = self.pin_to_module[pin]
                string += f"{str(module)} <--> {str(pin)}\n"
            string += "\n"
        
        return string[:-1] # Remove the last "\n"

    def copy(self, other: Circuit):
        self.width = other.width
        self.height = other.height

        self.module_to_pins = other.module_to_pins
        self.pin_to_module = other.pin_to_module

        self.modules = other.modules
        self.netlists = other.netlists
        self.connected_modules_pairs = other.connected_modules_pairs

    def get_pins_overlap_area(self, pin1: Pin, pin2: Pin) -> int:
        assert pin1 in self.pin_to_module
        assert pin2 in self.pin_to_module

        rect1 = Rectangle(pin1.dx, pin1.dy, pin1.width, pin1.height)
        rect2 = Rectangle(pin2.dx, pin2.dy, pin2.width, pin2.height)
        
        return get_rectangles_overlap_area(rect1, rect2)

    def connect_module(self, module: Module, pins: list[Pin]):
        assert 0 <= module.x + module.width <= self.width
        assert 0 <= module.y + module.height <= self.height

        self.module_to_pins[module] = pins

        for pin in pins:
            assert 0 <= pin.dx + pin.width <= module.width
            assert 0 <= pin.dy + pin.height <= module.height

            self.pin_to_module[pin] = module

        for i in range(len(pins)-1):
            pin1 = pins[i]
            for j in range(i+1, len(pins)):
                pin2 = pins[j]

                assert self.get_pins_overlap_area(pin1, pin2) == 0

        self.modules.append(module)

    def define_netlist(self, netlist: Netlist):
        self.netlists.append(netlist)

        for i in range(len(netlist)-1):
            module1 = netlist[i]
            for j in range(i+1, len(netlist)):
                module2 = netlist[j]

                self.connected_modules_pairs.add((module1, module2))
                self.connected_modules_pairs.add((module2, module1))

    def _get_netlist_bounding_box(self, netlist: Netlist) -> int:
        assert netlist in self.netlists

        min_x, min_y = self.width, self.height
        max_x, max_y = 0, 0

        for pin in netlist.pins:
            module = self.pin_to_module[pin]

            pin_start_x = module.x + pin.dx
            pin_start_y = module.y + pin.dy

            min_x = min(min_x, pin_start_x)
            min_y = min(min_y, pin_start_y)

            pin_end_x = pin_start_x + pin.width
            pin_end_y = pin_start_y + pin.height

            max_x = max(max_x, pin_end_x)
            max_y = max(max_y, pin_end_y)

        base = max_x - min_x
        height = max_y - min_y

        return base + height # Half-perimeter

    def get_bounding_boxes_total(self) -> int:
        return sum(self._get_netlist_bounding_box(netlist) for netlist in self.netlists)

    def get_avg_module_area(self) -> float:
        return sum(module.area for module in self.modules) / self.num_modules

    def get_modules_overlap_area(self, module1: Module, module2: Module) -> int:
        assert module1 in self.modules
        assert module2 in self.modules

        rect1 = Rectangle(module1.x, module1.y, module1.width, module1.height)
        rect2 = Rectangle(module2.x, module2.y, module2.width, module2.height)

        return get_rectangles_overlap_area(rect1, rect2)

    def is_feasible(self) -> bool:
        for i in range(self.num_modules-1):
            module1 = self.modules[i]
            for j in range(i+1, self.num_modules):
                module2 = self.modules[j]

                if self.get_modules_overlap_area(module1, module2) > 0:
                    return False

        return True

    def get_modules_distance_per_axis(self, module1: Module, module2: Module) -> DistancePerAxis:
        assert module1 in self.modules
        assert module2 in self.modules

        start_x1 = module1.x
        start_y1 = module1.y

        end_x1 = module1.x + module1.width
        end_y1 = module1.y + module1.height

        start_x2 = module2.x
        start_y2 = module2.y

        end_x2 = module2.x + module2.width
        end_y2 = module2.y + module2.height

        dx = max(start_x1 - end_x2, start_x2 - end_x1)
        dy = max(start_y1 - end_y2, start_y2 - end_y1)

        # Distances could be negative in case of overlaps,
        # we just set them to 0 in these scenarios
        dx = max(dx, 0)
        dy = max(dy, 0)

        return DistancePerAxis(dx, dy)

    def reflect_module(self, module: Module, axis: Axis):
        assert module in self.modules

        pins = self.module_to_pins[module]

        for pin in pins:
            if axis == Axis.X:
                pin.dy = module.height - (pin.dy + pin.height)
            elif axis == Axis.Y:
                pin.dx = module.width - (pin.dx + pin.width)
            else:
                raise Exception(f"Unrecognized Axis: {axis}")

    def translate_module(self, module: Module, direction: Direction, distance: int):
        distance = distance if direction.is_positive() else -distance
        if direction.is_vertical():
            module.y += distance
        else:
            module.x += distance

    def get_module_distance_until_boundary(self, module: Module, direction: Direction):
        assert direction.is_vertical() or direction.is_horizontal()
        assert direction.is_positive() or direction.is_negative()

        if direction == Direction.NORTH:
            distance = self.height - (module.y + module.height)
        elif direction == Direction.EAST:
            distance = self.width - (module.x + module.width)
        elif direction == Direction.SOUTH:
            distance = module.y
        elif direction == Direction.WEST:
            distance = module.x
        else:
            raise Exception(f"Unrecognized Direction: {direction}")

        return distance

    def get_module_distance_until_collision(self, module1: Module, direction: Direction) -> int:
        min_distance = self.get_module_distance_until_boundary(module1, direction)

        for i in range(self.num_modules):
            module2 = self.modules[i]

            distance = 0

            if direction.is_vertical():
                start_x1 = module1.x
                end_x1 = module1.x + module1.width

                start_x2 = module2.x
                end_x2 = module2.x + module2.width

                if start_x1 < end_x2 and start_x2 < end_x1:
                    if direction.is_positive():
                        distance = module2.y - (module1.y + module1.height)
                    elif direction.is_negative():
                        distance = module1.y - (module2.y + module2.height)
                        
            elif direction.is_horizontal():
                start_y1 = module1.y
                end_y1 = module1.y + module1.height

                start_y2 = module2.y
                end_y2 = module2.y + module2.height

                if start_y1 < end_y2 and start_y2 < end_y1:
                    if direction.is_positive():
                        distance = module2.x - (module1.x + module1.width)
                    elif direction.is_negative():
                        distance = module1.x - (module2.x + module2.width)

            if distance > 0:
                min_distance = min(min_distance, distance)

        return min_distance

    def translate_module_until_collision(self, module: Module, direction: Direction):
        distance = self.get_module_distance_until_collision(module, direction)
        self.translate_module(module, direction, distance)

    def rotate_module_cw(self, module: Module, angle: int):
        assert module in self.modules

        assert 0 <= angle <= 270
        assert angle % 90 == 0

        pins = self.module_to_pins[module]

        # In case the placement area isn't bigh enough for the rotation
        # we need to revert module and pins to their initial state
        module0, pins0 = deepcopy(module), deepcopy(pins)

        for _ in range(angle // 90):
            new_module_width = module.height
            new_module_height = module.width

            if 0 <= module.x + new_module_width <= self.width and 0 <= module.y + new_module_height <= self.height:
                for pin in pins:
                    pin.dx, pin.dy = pin.dy, module.width - (pin.dx + pin.width)

                module.width = new_module_width
                module.height = new_module_height

            else:
                # When rotations aren't doable we (silently) backtrack to the original state.
                # This approach is useful because it doesn't require any additional
                # logic over the other transformations, which can always be performed                
                module.copy(module0)
                for pin, pin0 in zip(pins, pins0):
                    pin.copy(pin0)

                break

    @debug
    def DEBUG_sanity_check(self):
        assert self.width > 0
        assert self.height > 0

        assert len(self.module_to_pins) == self.num_modules

        assert all(len(netlist) <= len(self.pin_to_module) for netlist in self.netlists)

        for module, pins in self.module_to_pins.items():
            assert 0 <= module.x <= (self.width - module.width)
            assert 0 <= module.y <= (self.height - module.height)

            for pin in pins:
                assert 0 <= pin.dx + pin.width <= module.width
                assert 0 <= pin.dy + pin.height <= module.height

            for i in range(len(pins)-1):
                pin1 = pins[i]
                for j in range(i+1, len(pins)):
                    pin2 = pins[j]

                    assert self.get_pins_overlap_area(pin1, pin2) == 0
