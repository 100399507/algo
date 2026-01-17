import streamlit as st
import pandas as pd
import copy
from allocation_algo import solve_model, run_auto_bid_aggressive
from products_config import products, SELLER_GLOBAL_MOQ

st.set_page_config(page_title="Allocation Engine – Test UI", layout="wide")

# -----------------------------
# Session State Init
# -----------------------------
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

# -----------------------------
# Helpers
# -----------------------------
def snapshot(label):
    allocations, total_ca = solve_model(st.session_state.buyers, products)
    st.session_state.history.append({
        "label": label,
        "buyers": copy.deepcopy(st.session_state.buyers),
        "allocations": allocations,
        "total_ca": total_ca
    })

def buyers_to_df():
    rows = []
    for b in st.session_state.buyers:
        for pid, p in b["products"].items():
            rows.append({
                "Acheteur": b["name"],
                "Produit": pid,
                "Prix courant": p["current_price"],
                "Prix max": p["max_price"],
                "Qté désirée": p["qty_desired"],
                "MOQ produit": p["moq"],
                "Auto-bid": b.get("auto_bid", False)
            })
    return pd.DataFrame(rows)

# -----------------------------
# Sidebar – Add Buyer
# -----------------------------
st.sidebar.title("➕ Ajouter un acheteur")

with st.sidebar.form("add_buyer_form"):
    buyer_name = st.text_input("Nom acheteur")
    auto_bid = st.checkbox("Auto-bid activé", value=True)

    buyer_products = {}
    for p in products:
        st.markdown(f"**{p['name']} ({p['id']})**")

        # Quantité minimale = MOQ produit
        qty = st.number_input(
            f"Qté désirée – {p['id']}",
            min_value=p["seller_moq"],
            value=p["seller_moq"],
            step=p["seller_moq"]
        )

        # Prix minimum basé sur les prix actuels des autres acheteurs
        other_current_prices = [
            b["products"][p["id"]]["current_price"] 
            for b in st.session_state.buyers if p["id"] in b["products"]
        ]
        min_allowed_price = max(other_current_prices, default=p["starting_price"]) + 0.01

        current_price = st.number_input(
            f"Prix proposé – {p['id']}",
            min_value=min_allowed_price,
            value=min_allowed_price,
            step=0.01
        )

        max_price = st.number_input(
            f"Prix max – {p['id']}",
            min_value=current_price,
            value=current_price + 2.0,  # Valeur initiale, mais ne sera jamais modifiée par l'auto-bid
            step=0.01
        )

        buyer_products[p["id"]] = {
            "qty_desired": qty,
            "current_price": current_price,
            "max_price": max_price,
            "moq": p["seller_moq"]
        }

    simulate = st.form_submit_button("Simuler mon allocation")
    add_buyer = st.form_submit_button("Ajouter acheteur")

    # -----------------------------
    # Simulation
    # -----------------------------
    if simulate and buyer_name:
        # On simule uniquement les acheteurs existants avec auto-bid
        existing_buyers = run_auto_bid_aggressive(
            copy.deepcopy(st.session_state.buyers), products
        )
        temp_buyers = existing_buyers + [{
            "name": buyer_name,
            "products": copy.deepcopy(buyer_products),
            "auto_bid": False
        }]

        allocations, _ = solve_model(temp_buyers, products)

        sim_rows = []
        for pid, p in buyer_products.items():
            qty_alloc = allocations[buyer_name][pid]
            status = "Gagnant" if qty_alloc > 0 else "Perdant"
            sim_rows.append({
                "Produit": pid,
                "Qté souhaitée": p["qty_desired"],
                "Quantité allouée": qty_alloc,
                "Prix proposé": p["current_price"],
                "Statut": status
            })

        st.subheader("📊 Simulation allocation")
        st.dataframe(pd.DataFrame(sim_rows), use_container_width=True)

    # -----------------------------
    # Ajouter l'acheteur
    # -----------------------------
    if add_buyer and buyer_name:
        # Ajouter le nouvel acheteur avec sa saisie intacte
        st.session_state.buyers.append({
            "name": buyer_name,
            "products": copy.deepcopy(buyer_products),
            "auto_bid": auto_bid
        })

        # Exécuter l'auto-bid agressif uniquement sur les acheteurs existants
        new_buyer_obj = st.session_state.buyers[-1]
        other_buyers = [b for b in st.session_state.buyers if b["name"] != buyer_name]
        updated_buyers = run_auto_bid_aggressive(copy.deepcopy(other_buyers), products)
        st.session_state.buyers = updated_buyers + [new_buyer_obj]

        snapshot(f"Ajout acheteur {buyer_name}")
        st.success("Acheteur ajouté avec succès")

# -----------------------------
# Main – Data Overview
# -----------------------------
st.title("🧪 Interface de test – Allocation multi-acheteurs")

st.subheader("📦 Produits")
st.dataframe(pd.DataFrame(products), use_container_width=True)

st.subheader("👥 Acheteurs")
if st.session_state.buyers:
    st.dataframe(buyers_to_df(), use_container_width=True)
else:
    st.info("Aucun acheteur pour le moment")

# -----------------------------
# Allocation Controls
# -----------------------------
st.subheader("⚙️ Actions")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶️ Lancer allocation"):
        snapshot("Allocation manuelle")

with col2:
    if st.button("🤖 Auto-bid agressif"):
        st.session_state.buyers = run_auto_bid_aggressive(
            st.session_state.buyers, products
        )
        snapshot("Auto-bid")

with col3:
    if st.button("🧹 Reset"):
        st.session_state.buyers = []
        st.session_state.history = []

# -----------------------------
# Current Allocation
# -----------------------------
if st.session_state.history:
    last = st.session_state.history[-1]
    st.subheader("📊 Allocation actuelle")
    alloc_rows = []

    for buyer_data in last["buyers"]:
        buyer_name = buyer_data["name"]
        for pid, qty in last["allocations"][buyer_name].items():
            current_price = buyer_data["products"][pid]["current_price"]
            alloc_rows.append({
                "Acheteur": buyer_name,
                "Produit": pid,
                "Quantité allouée": qty,
                "Prix courant": current_price,
                "CA ligne": qty * current_price
            })

    st.dataframe(pd.DataFrame(alloc_rows), use_container_width=True)
    st.metric("💰 Chiffre d'affaires total", f"{last['total_ca']:.2f} €")

# -----------------------------
# History & Analysis
# -----------------------------
st.subheader("🕒 Historique des itérations")

if st.session_state.history:
    history_df = pd.DataFrame([
        {
            "Itération": i,
            "Label": h["label"],
            "Acheteurs": len(h["buyers"]),
            "CA": h["total_ca"]
        }
        for i, h in enumerate(st.session_state.history)
    ])
    st.dataframe(history_df, use_container_width=True)

    selected = st.selectbox(
        "Voir détail itération",
        options=range(len(st.session_state.history))
    )
    hist = st.session_state.history[selected]

    # Tableau détaillé avec current_price
    detail_rows = []
    for b in hist["buyers"]:
        buyer_name = b["name"]
        for pid, p in b["products"].items():
            detail_rows.append({
                "Acheteur": buyer_name,
                "Produit": pid,
                "Qté allouée": hist["allocations"][buyer_name][pid],
                "Prix courant": p["current_price"],
                "Prix max": p["max_price"]
            })
    st.dataframe(pd.DataFrame(detail_rows), use_container_width=True)
else:
    st.info("Aucune itération enregistrée")
