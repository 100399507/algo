import streamlit as st
import pandas as pd
import copy

from allocation_algo import solve_model, run_auto_bid_aggressive
from products_config import products

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Allocation Engine – Test UI",
    layout="wide"
)

# =========================================================
# SESSION STATE INIT
# =========================================================
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

if "reset_form" not in st.session_state:
    st.session_state.reset_form = False

# =========================================================
# HELPERS
# =========================================================
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
                "Auto-bid": b["auto_bid"]
            })
    return pd.DataFrame(rows)

# =========================================================
# SIDEBAR – ADD BUYER
# =========================================================
st.sidebar.title("➕ Ajouter un acheteur")

# Reset logic
if st.session_state.reset_form:
    st.session_state.clear()
    st.session_state.buyers = []
    st.session_state.history = []
    st.session_state.reset_form = False

with st.sidebar.form("add_buyer", clear_on_submit=True):

    buyer_name = st.text_input("Nom acheteur")
    auto_bid = st.checkbox("Auto-bid activé", value=True)

    buyer_products = {}

    for p in products:
        st.markdown(f"### {p['name']} ({p['id']})")

        volume_multiple = p["volume_multiple"]
        max_qty_allowed = p["total_qty"]

        # -----------------------------
        # Quantité bloquée par stock
        # -----------------------------
        qty = st.number_input(
            f"Qté désirée – {p['id']}",
            min_value=0,
            max_value=max_qty_allowed,
            step=volume_multiple,
            value=volume_multiple
        )

        if qty % volume_multiple != 0:
            st.warning("⚠️ Quantité invalide (multiple requis)")

        # -----------------------------
        # Prix courant > existants
        # -----------------------------
        if st.session_state.buyers:
            existing_prices = [
                b["products"][p["id"]]["current_price"]
                for b in st.session_state.buyers
            ]
            min_price_allowed = max(existing_prices) + 0.1
        else:
            min_price_allowed = p["starting_price"]

        price = st.number_input(
            f"Prix courant – {p['id']}",
            min_value=min_price_allowed,
            value=min_price_allowed,
            step=0.05
        )

        # -----------------------------
        # Prix max (auto-bid sécurisé)
        # -----------------------------
        if st.session_state.buyers:
            existing_max = [
                b["products"][p["id"]]["max_price"]
                for b in st.session_state.buyers
            ]
            recommended_max = max(existing_max) + 0.5
        else:
            recommended_max = price

        max_price = st.number_input(
            f"Prix max – {p['id']}",
            min_value=price,
            value=recommended_max,
            step=0.05
        )

        buyer_products[p["id"]] = {
            "qty_desired": qty,
            "current_price": price,
            "max_price": max_price,
            "moq": p["seller_moq"]
        }

        # -----------------------------
        # Simulation position gagnante
        # -----------------------------
        if buyer_name:
            simulated_buyers = copy.deepcopy(st.session_state.buyers)
            simulated_buyers.append({
                "name": buyer_name,
                "products": buyer_products,
                "auto_bid": auto_bid
            })

            try:
                allocs, _ = solve_model(simulated_buyers, products)
                alloc_qty = allocs.get(buyer_name, {}).get(p["id"], 0)

                if alloc_qty > 0:
                    st.success("🟢 Position gagnante")
                else:
                    st.warning("🔴 Position perdante")
            except:
                st.info("ℹ️ En attente de simulation")

    submit = st.form_submit_button("🛒 Acheter / Ajouter")

# =========================================================
# ADD BUYER ACTION
# =========================================================
if submit and buyer_name:

    st.session_state.buyers.append({
        "name": buyer_name,
        "products": buyer_products,
        "auto_bid": auto_bid
    })

    # Auto-bid sans toucher à l'algo
    st.session_state.buyers = run_auto_bid_aggressive(
        st.session_state.buyers,
        products
    )

    snapshot(f"Ajout acheteur {buyer_name}")
    st.sidebar.success("Acheteur ajouté")

# =========================================================
# MAIN UI
# =========================================================
st.title("🧪 Allocation multi-acheteurs")

st.subheader("📦 Produits")
st.dataframe(pd.DataFrame(products), use_container_width=True)

st.subheader("👥 Acheteurs")
if st.session_state.buyers:
    st.dataframe(buyers_to_df(), use_container_width=True)
else:
    st.info("Aucun acheteur")

# =========================================================
# CURRENT ALLOCATION
# =========================================================
if st.session_state.history:
    last = st.session_state.history[-1]

    st.subheader("📊 Allocation actuelle")
    rows = []

    for buyer in last["buyers"]:
        for pid, qty in last["allocations"][buyer["name"]].items():
            price = buyer["products"][pid]["current_price"]
            rows.append({
                "Acheteur": buyer["name"],
                "Produit": pid,
                "Quantité": qty,
                "Prix": price,
                "CA": qty * price
            })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.metric("💰 CA total", f"{last['total_ca']:.2f} €")

# =========================================================
# HISTORY
# =========================================================
st.subheader("🕒 Historique")

if st.session_state.history:
    hist_df = pd.DataFrame([
        {
            "Itération": i,
            "Label": h["label"],
            "Acheteurs": len(h["buyers"]),
            "CA": h["total_ca"]
        }
        for i, h in enumerate(st.session_state.history)
    ])
    st.dataframe(hist_df, use_container_width=True)
else:
    st.info("Aucune itération")
