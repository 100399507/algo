import streamlit as st
import pandas as pd
import copy
from allocation_algo import (
    solve_model,
    run_auto_bid_aggressive,
    calculate_recommendations
)
from products_config import products, SELLER_GLOBAL_MOQ

st.set_page_config(page_title="Allocation Engine – Test UI", layout="wide")

# -----------------------------
# Session State Init
# -----------------------------
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

if "positioning" not in st.session_state:
    st.session_state.positioning = None

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

with st.sidebar.form("add_buyer"):
    buyer_name = st.text_input("Nom acheteur")
    auto_bid = st.checkbox("Auto-bid activé", value=True)

    buyer_products = {}
    can_submit = True

    for p in products:
        st.markdown(f"**{p['name']} ({p['id']})**")

        # Quantité initiale = multiple produit
        qty = st.number_input(
            f"Qté désirée – {p['id']}",
            min_value=p["volume_multiple"],
            max_value=p["stock"],
            step=p["volume_multiple"],
            value=p["volume_multiple"]
        )

        # Prix courant initialisé au prix max de la simulation précédente
        last_prices = [b["products"][p["id"]]["current_price"] for b in st.session_state.buyers] if st.session_state.buyers else []
        min_price = max(last_prices) + 0.01 if last_prices else p["starting_price"]
        price = st.number_input(
            f"Prix proposé – {p['id']}",
            min_value=min_price,
            value=min_price,
            step=0.01
        )

        max_price = st.number_input(
            f"Prix max – {p['id']}",
            min_value=price,
            value=price,
            step=0.01
        )

        # Vérification MOQ vendeur
        if qty < p["seller_moq"]:
            st.warning(f"Quantité pour {p['id']} inférieure à MOQ vendeur ({p['seller_moq']})")
            can_submit = False

        # Stock max
        if qty > p["stock"]:
            st.warning(f"Quantité pour {p['id']} ne peut dépasser le stock ({p['stock']})")
            can_submit = False

        buyer_products[p["id"]] = {
            "qty_desired": qty,
            "current_price": price,
            "max_price": max_price,
            "moq": p["seller_moq"]
        }

    submitted = st.form_submit_button("Ajouter l’acheteur", disabled=not can_submit)

    if submitted and buyer_name:
        new_buyer = {
            "name": buyer_name,
            "products": buyer_products,
            "auto_bid": auto_bid
        }

        # Simulation de positionnement pour afficher GAGNANT/PERDANT
        test_buyers = copy.deepcopy(st.session_state.buyers) + [new_buyer]
        alloc, _ = solve_model(test_buyers, products)
        won = any(alloc.get(buyer_name, {}).get(pid, 0) > 0 for pid in buyer_products)
        st.session_state.positioning = "🟢 GAGNANT" if won else "🔴 PERDANT"

        # Ajout réel
        st.session_state.buyers.append(new_buyer)

        # Auto-bid global
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)

        snapshot(f"Ajout acheteur {buyer_name}")

        # Réinitialisation formulaire
        st.experimental_set_query_params()
        st.success(f"Acheteur ajouté – Position: {st.session_state.positioning}")

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
        st.session_state.positioning = None

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
    st.json(hist["allocations"])
else:
    st.info("Aucune itération enregistrée")
