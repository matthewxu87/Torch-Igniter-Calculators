"""Size fuel and oxidizer mass flows for a required heat release using Cantera.

Supply --power-kj-s and --phi, or enter them at the prompts.
Edit DEFAULTS below to select fuel, oxidizer, and inlet conditions.
Power is in kJ/s (kW). Phi is (fuel/oxidizer)/(stoichiometric fuel/oxidizer):
below 1 is lean, above 1 is rich. Heat release is the reactant-to-product
enthalpy decrease at the inlet temperature, with product composition frozen
at the adiabatic equilibrium state and water remaining gaseous. This is an
ideal chemical heat release, not heat transferred to the torch hardware.
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
    "fuel": "H2:2",             # Examples: "H2:1", "CH4:0.8, H2:0.2"
    "oxidizer": "O2:1",         # Oxygen; for dry air use "O2:1, N2:3.76"
    "temperature_k": 300.0,
    "pressure_bar": 15,
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
    phi=1.0,
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


def calculate_mass_flows(
    power_kj_s,
    phi,
    fuel=DEFAULTS["fuel"],
    oxidizer=DEFAULTS["oxidizer"],
    temperature_k=DEFAULTS["temperature_k"],
    pressure_bar=DEFAULTS["pressure_bar"],
    mechanism=DEFAULTS["mechanism"],
):
    """Return stream flows [kg/s] and ideal mixture heat release [kJ/kg].

    Retain the HP equilibrium product composition when evaluating its
    enthalpy at inlet temperature. Subtracting the hot HP enthalpy directly
    would give zero because the adiabatic calculation conserves enthalpy.
    """
    for name, value in (("power_kj_s", power_kj_s), ("phi", phi),
                        ("temperature_k", temperature_k), ("pressure_bar", pressure_bar)):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and greater than zero")
    gas = ct.Solution(mechanism)
    pressure_pa = pressure_bar * 100_000
    gas.TP = temperature_k, pressure_pa
    stoich_of = gas.stoich_air_fuel_ratio(fuel, oxidizer, basis="mole")
    actual_of = stoich_of / phi
    if not math.isfinite(actual_of) or actual_of <= 0:
        raise ValueError("Fuel and oxidizer must define a positive finite mass ratio")
    gas.set_equivalence_ratio(phi, fuel, oxidizer, basis="mole")
    reactant_enthalpy = gas.enthalpy_mass
    gas.equilibrate("HP")
    flame_temperature_k = gas.T
    gas.TP = temperature_k, pressure_pa  # Frozen products; do not re-equilibrate.
    heat_release_kj_kg = (reactant_enthalpy - gas.enthalpy_mass) / 1000.0
    if not math.isfinite(heat_release_kj_kg) or heat_release_kj_kg <= 0:
        raise ValueError("Specified mixture does not provide positive heat release")
    total_flow = power_kj_s / heat_release_kj_kg
    fuel_flow = total_flow / (1.0 + actual_of)
    oxidizer_flow = total_flow - fuel_flow
    if not all(math.isfinite(x) and x > 0 for x in (fuel_flow, oxidizer_flow)):
        raise ValueError("Requested inputs exceed the numerical range for mass flows")
    return {
        "fuel_kg_s": fuel_flow,
        "oxidizer_kg_s": oxidizer_flow,
        "total_kg_s": total_flow,
        "heat_release_kj_kg": heat_release_kj_kg,
        "oxidizer_fuel_mass_ratio": actual_of,
        "flame_temperature_k": flame_temperature_k,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fuel", default=DEFAULTS["fuel"], help="Fuel mole composition")
    parser.add_argument("--oxidizer", default=DEFAULTS["oxidizer"], help="Oxidizer mole composition")
    parser.add_argument("--power-kj-s", type=positive_number, help="Required ideal heat release [kJ/s = kW]; prompted if omitted")
    parser.add_argument("--phi", type=positive_number, help="Equivalence ratio: <1 lean, 1 stoichiometric, >1 rich; prompted if omitted")
    parser.add_argument("--temperature-k", type=positive_number, default=DEFAULTS["temperature_k"], help="Common reactant inlet temperature [K]")
    parser.add_argument("--pressure-bar", type=positive_number, default=DEFAULTS["pressure_bar"], help="Absolute pressure [bar]")
    parser.add_argument("--mechanism", default=DEFAULTS["mechanism"], help="Cantera mechanism YAML file")
    args = parser.parse_args()
    try:
        if args.power_kj_s is None:
            args.power_kj_s = positive_number(input("Required heat release [kJ/s = kW]: "))
        if args.phi is None:
            args.phi = positive_number(input("Equivalence ratio phi (<1 lean, >1 rich): "))
        result = calculate_mass_flows(**vars(args))
    except (ct.CanteraError, ValueError, argparse.ArgumentTypeError, EOFError) as exc:
        parser.exit(1, f"Calculation failed: {exc}\n")

    print("Fuel and oxidizer mass flows (ideal equilibrium heat release)")
    print(f"Fuel: {args.fuel} | Oxidizer: {args.oxidizer}")
    print(f"Inlet: {args.temperature_k:g} K | Pressure: {args.pressure_bar:g} bar absolute")
    print(f"Equivalence ratio: {args.phi:g} | Mechanism: {args.mechanism}")
    print(f"Required heat release: {args.power_kj_s:g} kJ/s (kW)")
    print(f"\nFuel mass flow:     {result['fuel_kg_s']:.8g} kg/s")
    print(f"Oxidizer mass flow: {result['oxidizer_kg_s']:.8g} kg/s")
    print(f"Total mass flow:    {result['total_kg_s']:.8g} kg/s")
    print(f"\nMixture heat release: {result['heat_release_kj_kg']:.6g} kJ/kg")
    print(f"Adiabatic flame temperature: {result['flame_temperature_k']:.1f} K")
    print("Basis: frozen equilibrium products evaluated at inlet temperature; gaseous water.")
    print("Ideal chemical heat release; excludes heat-transfer efficiency and combustion kinetics.")


if __name__ == "__main__":
    main()
