from __future__ import annotations
import os
from functools import wraps
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import circuit

def debug(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if os.getenv("DEBUG", "0") == "1":
            return func(*args, **kwargs)
    return wrapper

def draw_circuit(circuit: circuit.Circuit, scale: float = 0.2, dpi: int = 300, value: None | int = None, save_path: None | str = None):
    fig_width = circuit.width * scale
    fig_height = circuit.height * scale
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
    
    ax.set_aspect('equal')
    ax.set_xlim(0, circuit.width)
    ax.set_ylim(0, circuit.height)
    ax.set_xticks([])
    ax.set_yticks([])
    
    for module, pin in circuit.modules_pins.items():
        pin_x = module.x + pin.dx
        pin_y = module.y + pin.dy
        
        pin_rectangle = Rectangle((pin_x, pin_y), pin.width, pin.height,
                                  fill=True, color="orange", alpha=0.5)
        ax.add_patch(pin_rectangle)

    
    for i, module in enumerate(circuit.modules):
        rectangle = Rectangle((module.x, module.y), module.width, module.height,
                              fill=False, edgecolor="black")
        ax.add_patch(rectangle)
    
    for netlist in circuit.netlists:
        xs = [circuit.pins_modules[pin].x + pin.dx + pin.width/2 for pin in netlist.pins]
        ys = [circuit.pins_modules[pin].y + pin.dy + pin.height/2 for pin in netlist.pins]
        
        ax.plot(xs, ys, linestyle="--", linewidth=0.5, color="gray")

    title_str = f"Circuit ({circuit.width}x{circuit.height})"
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
