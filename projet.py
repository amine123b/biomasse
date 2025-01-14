import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import plotly.express as px

# Mise à jour des types de biomasse avec les données du tableau et de nouvelles biomasses
BIOMASS_TYPES = {
    "Bois bûche": {"pci": 3.8, "pcs": 5.1, "C": 49, "H": 6, "O": 44, "N": 0.3, "moisture": 20, "price": 75},
    "Granulés de bois": {"pci": 4.6, "pcs": 5.1, "C": 47.1, "H": 5.5, "O": 42.5, "N": 0.3, "moisture": 6, "price": 289},
    "Plaquettes forestières": {"pci": 2.2, "pcs": 2.4, "C": 49.5, "H": 6, "O": 44, "N": 0.5, "moisture": 40, "price": 100},
    "Paille de maïs": {"pci": 4.3, "pcs": 5.07, "C": 46.1, "H": 5.9, "O": 40.1, "N": 0.8, "moisture": 15, "price": 63},
    "Pailles de blé": {"pci": 4, "pcs": 5.02, "C": 43.4, "H": 6, "O": 44.5, "N": 0.8, "moisture": 15, "price": 28},
    "Miscanthus déchiqueté": {"pci": 4.4, "pcs": 5.3, "C": 49, "H": 6, "O": 40, "N": 0.15, "moisture": 10, "price": 65},
    "Chêne": {"pci": 3.8, "pcs": 5.4, "C": 49.5, "H": 5.4, "O": 44.7, "N": 0.3, "moisture": 20, "price": 360},
    "Grignons d'olive": {"pci": 5.7, "pcs": 6.1, "C": 55.1, "H": 7, "O": 33.9, "N": 1.3, "moisture": 7, "price": 159},
    "Coques de noix": {"pci": 5.2, "pcs": 5.8, "C": 54, "H": 6.5, "O": 35, "N": 1.0, "moisture": 8, "price": 180},
    "Tiges de colza": {"pci": 4.2, "pcs": 5.0, "C": 46, "H": 5.8, "O": 42, "N": 0.6, "moisture": 12, "price": 90},
    "Marc de raisin": {"pci": 3.5, "pcs": 4.2, "C": 48, "H": 6, "O": 40, "N": 0.7, "moisture": 25, "price": 50},
}

# Fonction de calcul des pertes thermiques et du rendement

def calculate_thermal_efficiency(power_demand, moisture):
    efficiency = 0.85 - (moisture / 100) * 0.1
    return max(0.5, min(efficiency, 0.9))

def calculate_technical_efficiency(thermal_eff, moisture, operation_duration):
    degradation_factor = 1 - (moisture / 100) * 0.05
    return max(0.4, min(thermal_eff * degradation_factor, 0.9))

def calculate_thermal_losses(energy_output, moisture):
    radiation_losses = 0.02 * energy_output
    convection_losses = 0.03 * energy_output
    exhaust_losses = 0.05 * energy_output * (1 + moisture / 100)
    return radiation_losses, convection_losses, exhaust_losses

def calculate_additional_results(temp_ambient, temp_fumes, biomass_consumption, mass_flow_biomass, mass_flow_fumes, heat_capacity_fumes, wall_area, trans_coeff):
    volume_co2 = mass_flow_fumes * 0.57
    volume_h2o = mass_flow_fumes * 0.21
    volume_humidity = mass_flow_fumes * 0.14
    co2_percentage = 18.78  # Example from table
    fumes_losses = mass_flow_fumes * heat_capacity_fumes * (temp_fumes - temp_ambient)
    ambient_losses = wall_area * trans_coeff * (temp_fumes - temp_ambient)
    return {
        "Volume CO2 (m³)": volume_co2,
        "Volume H2O (m³)": volume_h2o,
        "Volume Humidité (m³)": volume_humidity,
        "Teneur en CO2 (%)": co2_percentage,
        "Pertes fumées (kW)": fumes_losses,
        "Pertes ambiance (kW)": ambient_losses
    }

def calculate_combustion_properties(pci, moisture):
    pouvoir_comburivor = pci * 3.76  # Hypothèse d'exemple
    pouvoir_fumigene_sec = pci * 1.1
    pouvoir_fumigene_humide = pouvoir_fumigene_sec * (1 + moisture / 100)
    return pouvoir_comburivor, pouvoir_fumigene_sec, pouvoir_fumigene_humide

def calculate_base_results(fuel_type, power_demand, operation_duration, biomass_price):
    properties = BIOMASS_TYPES[fuel_type]
    moisture = properties["moisture"]
    pci = properties["pci"]
    pcs = properties["pcs"]
    energy_output = power_demand * 1000
    thermal_eff = calculate_thermal_efficiency(power_demand, moisture)
    technical_eff = calculate_technical_efficiency(thermal_eff, moisture, operation_duration)
    radiation_losses, convection_losses, exhaust_losses = calculate_thermal_losses(
        energy_output, moisture
    )
    fuel_required = energy_output / (pci * 1000 * thermal_eff)
    total_fuel = fuel_required * operation_duration
    fuel_cost = total_fuel * biomass_price / 1000
    thermal_losses = radiation_losses + convection_losses + exhaust_losses
    savings = fuel_cost * 0.15  # Exemple : économie estimée (15% des coûts)
    co2_emissions = fuel_required * properties["C"] / 100

    # Calcul des pouvoirs comburivor et fumigènes
    pouvoir_comburivor, pouvoir_fumigene_sec, pouvoir_fumigene_humide = calculate_combustion_properties(pci, moisture)

    return {
        "PCI (kWh/kg)": pci,
        "PCS (kWh/kg)": pcs,
        "Moisture (%)": moisture,
        "Carbone (%)": properties["C"],
        "Hydrogène (%)": properties["H"],
        "Oxygène (%)": properties["O"],
        "Azote (%)": properties["N"],
        "Prix Biomasse (dh/tonne)": biomass_price,
        "Energy Output (kWh)": energy_output,
        "Thermal Efficiency (%)": thermal_eff * 100,
        "Technical Efficiency (%)": technical_eff * 100,
        "Fuel Required (kg)": total_fuel,
        "Radiation Losses (kWh)": radiation_losses,
        "Convection Losses (kWh)": convection_losses,
        "Exhaust Losses (kWh)": exhaust_losses,
        "Thermal Losses (kWh)": thermal_losses,
        "Fuel Cost (dh)": fuel_cost,
        "Savings (dh)": savings,
        "CO2 Emissions (kg)": co2_emissions,
        "Pouvoir Comburivor (kWh/kg)": pouvoir_comburivor,
        "Pouvoir Fumigène Sec (kWh/kg)": pouvoir_fumigene_sec,
        "Pouvoir Fumigène Humide (kWh/kg)": pouvoir_fumigene_humide,
    }

# Fonction pour afficher les suggestions d'optimisation

def display_optimizations():
    st.subheader("Optimisations possibles")
    optimizations = [
        "1. Ajouter un économiseur pour récupérer la chaleur des gaz d'échappement.",
        "2. Améliorer l'isolation thermique pour réduire les pertes par radiation et convection.",
        "3. Installer un système d'alimentation automatisé pour stabiliser la combustion.",
        "4. Sécher la biomasse avant combustion pour augmenter son PCI.",
        "5. Ajouter des capteurs pour surveiller les émissions et optimiser la combustion.",
        "6. Utiliser un filtre électrostatique pour réduire les émissions de particules.",
        "7. Valoriser les cendres comme amendement agricole ou matériaux de construction.",
        "8. Intégrer un système de cogénération pour produire également de l'électricité.",
    ]
    for opt in optimizations:
        st.write(opt)

# Interface utilisateur
st.title("Analyse et Optimisation de la Biomasse")

# Sélection du type de biomasse
fuel_type = st.selectbox("Type de Biomasse", list(BIOMASS_TYPES.keys()))
st.write(f"Teneur en humidité: {BIOMASS_TYPES[fuel_type]['moisture']}%")
st.write(f"PCI: {BIOMASS_TYPES[fuel_type]['pci']} kWh/kg")
st.write(f"PCS: {BIOMASS_TYPES[fuel_type]['pcs']} kWh/kg")

# Entrées utilisateur
biomass_price_default = float(BIOMASS_TYPES[fuel_type].get('price', 0))  # Valeur par défaut sûre
power_demand = st.number_input("Demande en puissance (kW)", min_value=1.0, step=0.1)
operation_duration = st.number_input("Durée de fonctionnement (heures)", min_value=1, step=1)
biomass_price = st.number_input("Prix de la biomasse (dh/tonne)", value=biomass_price_default, step=1.0)

# Étude technique
st.header("Étude technique")
temp_ambient = st.number_input("Température ambiante (°C)", value=25.0, step=0.1)
temp_fumes = st.number_input("Température des fumées (°C)", value=130.0, step=0.1)
biomass_consumption = st.number_input("Consommation Biomasse (tonnes/mois)", value=2.0, step=0.1)
mass_flow_biomass = st.number_input("Débit massique de la biomasse (kg/s)", value=0.3, step=0.01)
mass_flow_fumes = st.number_input("Débit massique des fumées (kg/s)", value=1.8, step=0.01)
heat_capacity_fumes = st.number_input("Chaleur massique des fumées (J/kg.K)", value=1045.0, step=1.0)
wall_area = st.number_input("Surface de la paroi (m²)", value=2.0, step=0.1)
trans_coeff = st.number_input("Coefficient de transmission (W/m².°C)", value=0.03, step=0.01)

# Étude environnementale
st.header("Étude environnementale")
st.write("Analyse des émissions de CO2, H2O et autres gaz issus de la combustion.")
st.write("Impact environnemental basé sur le volume de gaz produit et l'efficacité énergétique.")

if st.button("Calculer et afficher les résultats", key="calculate", use_container_width=True):
    # Calculs principaux
    results = calculate_base_results(
        fuel_type=fuel_type,
        power_demand=power_demand,
        operation_duration=operation_duration,
        biomass_price=biomass_price
    )

    additional_results = calculate_additional_results(
        temp_ambient, temp_fumes, biomass_consumption,
        mass_flow_biomass, mass_flow_fumes, heat_capacity_fumes, wall_area, trans_coeff
    )

    results.update(additional_results)

    st.write("### Résultats globaux")
    st.write(results)

    # Affichage des graphiques interactifs catégorisés
    st.write("## Graphiques interactifs")

    # Graphiques des rendements
    st.subheader("Rendements")
    fig_efficiency = px.bar(
        x=["Rendement thermique", "Rendement technique"],
        y=[results["Thermal Efficiency (%)"], results["Technical Efficiency (%)"]],
        labels={"x": "Type de rendement", "y": "Pourcentage (%)"},
        title="Comparaison des rendements thermique et technique"
    )
    st.plotly_chart(fig_efficiency)

    # Graphique des coûts
    st.subheader("Coûts")
    years = np.arange(1, 21)
    cost_values = [results["Fuel Cost (dh)"] * y for y in years]
    fig_cost = px.line(
        x=years, y=cost_values,
        labels={"x": "Années", "y": "Coût total (dh)"},
        title="Évolution des coûts au cours des années"
    )
    st.plotly_chart(fig_cost)

    # Graphique des émissions
    st.subheader("Émissions de CO2")
    fig_emissions = px.bar(
        x=["CO2"],
        y=[results["CO2 Emissions (kg)"]],
        labels={"x": "Type d'émission", "y": "Émissions (kg)"},
        title="Émissions de CO2 issues de la combustion"
    )
    st.plotly_chart(fig_emissions)

    # Téléchargement des données
    csv_data = pd.DataFrame([results])
    csv_buffer = BytesIO()
    csv_data.to_csv(csv_buffer, index=False)
    st.download_button(
        label="Télécharger les résultats en CSV",
        data=csv_buffer.getvalue(),
        file_name="resultats_biomasse.csv",
        mime="text/csv",
        key="download_csv"
    )

if st.button("Optimiser", key="optimize", use_container_width=True):
    display_optimizations()
