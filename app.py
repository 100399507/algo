import streamlit as st
import copy
from allocation_algo import solve_model, run_auto_bid_aggressive, calculate_recommendations
from products_config import products, SELLER_GLOBAL_MOQ

st.set_page_config(page_title="Simulateur d'enchères", layout="wide")

st.title("💰 Simulateur d'enchères séquentiel")

# Initialisation des acheteurs
if "buyers" not in st.session_state:
    st.session_state.buyers = []

# -----------------------------------
# Formulaire pour ajouter un nouvel acheteur
# -----------------------------------
with st.form("nouvel_acheteur"):
    st.subheader("Ajouter un nouvel acheteur")
    name = st.text_input("Nom de l'acheteur", value=f"Acheteur_{len(st.session_state.buyers)+1}")
    auto_bid = st.checkbox("Activer auto-bid", value=True)

    buyer_products = {}
    for product in products:
        st.markdown(f"**{product['name']}**")
        current_price = st.number_input(f"Prix actuel ({product['name']})", min_value=product['starting_price'], value=product['starting_price']+0.5)
        max_price = st.number_input(f"Prix max ({product['name']})", min_value=current_price, value=current_price+5.0)
        qty_desired = st.number_input(f"Quantité désirée ({product['name']})", min_value=1, value=min(50, product['stock']//2))
        moq = st.number_input(f"MOQ ({product['name']})", min_value=1, value=min(30, qty_desired//2))

        buyer_products[product['id']] = {
            "current_price": current_price,
            "max_price": max_price,
            "qty_desired": qty_desired,
            "moq": moq
        }

    submitted = st.form_submit_button("Ajouter l'acheteur")
    if submitted:
        st.session_state.buyers.append({
            "name": name,
            "auto_bid": auto_bid,
            "products": buyer_products
        })
        st.success(f"Acheteur {name} ajouté!")

        # Auto-bid agressif
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)

# -----------------------------------
# Affichage des allocations
# -----------------------------------
if st.session_state.buyers:
    st.subheader("📊 Allocations actuelles")
    allocations, total_ca = solve_model(st.session_state.buyers, products)
    st.write(f"**CA total**: {total_ca:.2f}€")

    for product in products:
        st.markdown(f"### {product['name']} (Stock: {product['stock']})")
        cols = st.columns(len(st.session_state.buyers))
        for i, buyer in enumerate(st.session_state.buyers):
            alloc = allocations[buyer['name']][product['id']]
            cols[i].metric(label=buyer['name'], value=f"{alloc} unités")

# -----------------------------------
# Recommandations pour le prochain acheteur
# -----------------------------------
st.subheader("💡 Recommandations pour le prochain acheteur")
next_buyer_name = f"Acheteur_{len(st.session_state.buyers)+1}"
recommendations = calculate_recommendations(st.session_state.buyers, products, next_buyer_name)

for product in products:
    rec = recommendations[product['id']]
    st.markdown(f"**{product['name']}**")
    st.write(f"- Prix minimum pour entrer: {rec.get('min_price_to_enter', '⚠️ difficile')}")
    st.write(f"- Prix recommandé: {rec.get('recommended_price', '⚠️ difficile')}")
    st.write(f"- Allocation estimée: {rec.get('estimated_allocation', 0)}")
    st.write(f"- Stock restant: {rec.get('remaining_stock', product['stock'])}")
    st.write(f"- Stratégie: {rec.get('strategy', '')}")
