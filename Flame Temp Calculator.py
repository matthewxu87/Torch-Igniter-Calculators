"""Constant-pressure, adiabatic equilibrium flame temperature using Cantera.

Edit DEFAULTS below or run with --help for command-line options.
Assumes a premixed ideal gas with one common inlet temperature, no heat loss,
and chemical equilibrium (including gas-phase dissociation). Does not model
ignition, flame stability, heat transfer, or solid carbon formation.
Reference: https://cantera.org/stable/python/thermo.html
"""

import argparse
import math

import cantera as ct


# Compositions are relative mole amounts. Pressure is ABSOLUTE, not gauge.
DEFAULTS = {
    "fuel": "H2:1",             # Examples: "H2:1", "CH4:0.8, H2:0.2"
    "oxidizer": "O2:1", # Dry air approximation; use "O2:1" for oxygen
    "phi": 3.0,                  # <1 lean, 1 stoichiometric, >1 rich
    "temperature_k": 300.0,
    "pressure_bar": 50,
    "mechanism": "gri30.yaml",   # Fuel species must exist in this mechanism
}


def positive_number(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return number


def calculate_flame_temperature(
    fuel=DEFAULTS["fuel"],
    oxidizer=DEFAULTS["oxidizer"],
    phi=DEFAULTS["phi"],
    temperature_k=DEFAULTS["temperature_k"],
    pressure_bar=DEFAULTS["pressure_bar"],
    mechanism=DEFAULTS["mechanism"],
):
    """Return the equilibrated Cantera Solution; its T attribute is in kelvin."""
    for name, value in (("phi", phi), ("temperature_k", temperature_k),
                        ("pressure_bar", pressure_bar)):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and greater than zero")
    gas = ct.Solution(mechanism)
    gas.TP = temperature_k, pressure_bar * 100_000
    gas.set_equivalence_ratio(phi, fuel, oxidizer, basis="mole")
    # H = constant enthalpy (adiabatic); P = constant pressure.
    gas.equilibrate("HP")
    return gas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fuel", default=DEFAULTS["fuel"], help="Fuel mole composition")
    parser.add_argument("--oxidizer", default=DEFAULTS["oxidizer"], help="Oxidizer mole composition")
    parser.add_argument("--phi", type=positive_number, default=DEFAULTS["phi"], help="Equivalence ratio")
    parser.add_argument("--temperature-k", type=positive_number, default=DEFAULTS["temperature_k"], help="Common reactant inlet temperature [K]")
    parser.add_argument("--pressure-bar", type=positive_number, default=DEFAULTS["pressure_bar"], help="Absolute pressure [bar]")
    parser.add_argument("--mechanism", default=DEFAULTS["mechanism"], help="Cantera mechanism YAML file")
    args = parser.parse_args()
    try:
        gas = calculate_flame_temperature(**vars(args))
    except (ct.CanteraError, ValueError) as exc:
        parser.exit(1, f"Calculation failed: {exc}\n")

    print("Adiabatic equilibrium flame temperature (constant pressure)")
    print(f"Fuel: {args.fuel} | Oxidizer: {args.oxidizer}")
    print(f"Inlet: {args.temperature_k:g} K | Pressure: {args.pressure_bar:g} bar absolute")
    print(f"Equivalence ratio: {args.phi:g} | Mechanism: {args.mechanism}")
    print(f"\nFlame temperature: {gas.T:.1f} K / {gas.T - 273.15:.1f} deg C")
    print("\nEquilibrium products (mole fractions >= 0.0001):")
    for species, fraction in sorted(zip(gas.species_names, gas.X), key=lambda item: item[1], reverse=True):
        if fraction >= 0.0001:
            print(f"  {species:<8} {fraction:.6f}")
    print("\nIdeal adiabatic estimate; actual torch temperature depends on heat loss and mixing.")


if __name__ == "__main__":
    main()
