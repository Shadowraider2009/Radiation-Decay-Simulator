import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random
import math

def run_simulation():
    try:
        atoms = int(entry_atoms.get())
        power = int(entry_power.get())
        total_atoms = atoms * (10 ** power)
        length = entry_length.get()
        chance_input = entry_chance.get().strip()
    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numbers.")
        return

    # Determine decay mode
    if chance_input.lower() in ["none", ""]:
        stochastic = False
        chance = None
        decay_type = "Natural decay"
    else:
        stochastic = True
        chance = int(chance_input)
        decay_type = f"Chance 1/{chance}"

    # Reset variables
    initial_atoms = atoms
    year = 0
    half_life = None
    half_life_found = False
    years_list = []
    atoms_list = []

    # Clear output
    output_box.delete(1.0, tk.END)
    output_box.insert(tk.END, f"Starting with {total_atoms} atoms\n")

    if stochastic:
        # Exact stochastic simulation
        while atoms > 0:
            years_list.append(year)
            atoms_list.append(atoms * (10 ** power))

            for _ in range(atoms):
                year += 1 / atoms  # exact per-atom increment
                if random.randint(1, chance) == 1:
                    atoms -= 1
                    if atoms == 0:
                        break  # stop inner loop if all decayed

            if not half_life_found and atoms <= 0.5 * initial_atoms:
                half_life = year
                half_life_found = True
                output_box.insert(tk.END, f"Half-life ≈ {round(half_life,3)} {length}\n")
    else:
        # Deterministic decay, stop at 0 atoms
        decay_constant = 0.1  # keep your original speed
        total = initial_atoms
        dt = 1.0
        while total > 0:
            years_list.append(year)
            atoms_list.append(total * (10 ** power))

            total = total * math.exp(-decay_constant * dt)
            year += dt

            if not half_life_found and total <= 0.5 * initial_atoms:
                half_life = year
                half_life_found = True
                output_box.insert(tk.END, f"Half-life ≈ {round(half_life,3)} {length}\n")

            if total < 1:
                total = 0  # stop at 0 atoms

    # Output final result
    if half_life:
        output_box.insert(tk.END, f"\nSimulation ended. Half-life ≈ {round(half_life,3)} {length}\n")
    else:
        output_box.insert(tk.END, "\nSimulation ended. Half-life was not reached.\n")

    # Show graph
    show_graph(years_list, atoms_list, half_life, length, total_atoms, decay_type)


def show_graph(years_list, atoms_list, half_life, length, total_atoms, decay_type):
    global fig, ax, canvas

    plt.close("all")
    fig, ax = plt.subplots()
    ax.plot(years_list, atoms_list, label="Atoms Left")

    if half_life:
        ax.axvline(half_life, color="red", linestyle="--",
                   label=f"Half-life ≈ {round(half_life,3)} {length}")

    ax.set_xlabel(f"Time ({length})")
    ax.set_ylabel("Atoms Remaining")
    ax.set_title(f"Decay Simulation: {int(total_atoms)} atoms, {decay_type}")
    ax.legend()
    ax.grid(True)

    graph_window = tk.Toplevel(root)
    graph_window.title("Decay Graph")

    canvas = FigureCanvasTkAgg(fig, master=graph_window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    tk.Button(graph_window, text="Rerun Simulation", command=run_simulation).pack(pady=10)


# UI Setup
root = tk.Tk()
root.title("Radioactive Decay Simulator")

frame_inputs = tk.Frame(root)
frame_inputs.pack(pady=10)

tk.Label(frame_inputs, text="Atoms (note, the larger this is, the more exact the graph):").grid(row=0, column=0)
entry_atoms = tk.Entry(frame_inputs)
entry_atoms.grid(row=0, column=1)

tk.Label(frame_inputs, text="Power (10^):").grid(row=1, column=0)
entry_power = tk.Entry(frame_inputs)
entry_power.grid(row=1, column=1)

tk.Label(frame_inputs, text="Time unit:").grid(row=2, column=0)
entry_length = tk.Entry(frame_inputs)
entry_length.grid(row=2, column=1)

tk.Label(frame_inputs, text="Chance of Decay (1/x) or 'none':").grid(row=3, column=0)
entry_chance = tk.Entry(frame_inputs)
entry_chance.grid(row=3, column=1)

tk.Button(root, text="Run Simulation", command=run_simulation).pack(pady=5)

output_box = tk.Text(root, height=10, width=50)
output_box.pack(pady=10)

root.mainloop()
