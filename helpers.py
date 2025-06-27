from __future__ import annotations
import os
from functools import wraps
from dataclasses import dataclass
import matplotlib.pyplot as plt
import matplotlib.patches
import circuit

def debug(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if os.getenv("DEBUG", "0") == "1":
            return func(*args, **kwargs)
    return wrapper

@dataclass
class Rectangle:
    x: int
    y: int
    width: int
    height: int

def get_rectangles_overlap_area(rect1: Rectangle, rect2: Rectangle) -> int:
    start_x1 = rect1.x
    start_y1 = rect1.y

    end_x1 = rect1.x + rect1.width
    end_y1 = rect1.y + rect1.height

    start_x2 = rect2.x
    start_y2 = rect2.y

    end_x2 = rect2.x + rect2.width
    end_y2 = rect2.y + rect2.height

    base = min(end_x1, end_x2) - max(start_x1, start_x2)
    height = min(end_y1, end_y2) - max(start_y1, start_y2)

    # If they don't overlap, the area is just set to 0
    base = max(base, 0)
    height = max(height, 0)

    return base * height

def draw_circuit(circuit: circuit.Circuit, scale: float = 0.2, dpi: int = 300, value: None | int = None, save_path: None | str = None):
    fig_width = circuit.width * scale
    fig_height = circuit.height * scale
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
    
    ax.set_aspect('equal')
    ax.set_xlim(0, circuit.width)
    ax.set_ylim(0, circuit.height)
    ax.set_xticks([])
    ax.set_yticks([])
    
    for module, pins in circuit.module_to_pins.items():
        for pin in pins:
            pin_x = module.x + pin.dx
            pin_y = module.y + pin.dy
            
            pin_rectangle = matplotlib.patches.Rectangle((pin_x, pin_y), pin.width, pin.height,
                                      fill=True, color="orange", alpha=0.5)
            ax.add_patch(pin_rectangle)

    
    for i, module in enumerate(circuit.modules):
        rectangle = matplotlib.patches.Rectangle((module.x, module.y), module.width, module.height,
                              fill=False, edgecolor="black")
        ax.add_patch(rectangle)
    
    for netlist in circuit.netlists:
        xs = [circuit.pin_to_module[pin].x + pin.dx + pin.width/2 for pin in netlist.pins]
        ys = [circuit.pin_to_module[pin].y + pin.dy + pin.height/2 for pin in netlist.pins]
        
        ax.plot(xs, ys, linestyle="--", linewidth=0.5, color="gray")

    feasible_str = "Feasible" if circuit.is_feasible() else "Unfeasible"
    title_str = f"{feasible_str} Circuit ({circuit.width}x{circuit.height})"
    if value is not None:
        title_str += f", f = {value}"

    plt.title(title_str)
    plt.xlabel("X")
    plt.ylabel("Y")
    
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
    else:
        plt.show()

    plt.close(fig)
