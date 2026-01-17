import streamlit as st
import pandas as pd
import copy

from allocation_algo import solve_model, run_auto_bid_aggressive
from products_config import products, SELLER_GLOBAL_MOQ

st.set_page_config(page_title="Allocation Engine – Test UI", layout="wide")

# ======================================================
# Session state
# ======================================================
if "buyers" not in st.session_state:
    st.session_state.buyers = []

if "history" not in st.session_state:
    st.session_state.history = []

if "positioning" not in st.session_state:
    st.session_state.positioning = None


# ======================================================
# Helpers
# ======================================================
def snapshot(label):
    alloc, ca = solve_model(st.session_state.buyers, products)
    st.session_state.history.append({
        "label": label,
        "buyers": copy.deepcopy(st.session_state.buyers),
        "allocations": alloc,
        "total_ca": ca
    })


def get_market_max_price(prod_id):
    prices = [b["products"][prod_id]["current_price"] for b in st.session_state.buyers]
    return max(prices) if prices else None


def buyers_df():
    rows = []
    for b in st.session_state.buyers:
        for pid, p in b["products"].items():
            rows.append({
                "Acheteur": b["name"],
                "Produit": pid,
                "Prix courant": p["current_price"],
                "Prix max": p["max_price"],
                "Quantité souhaitée": p["qty_desired"],
                "Auto-bid": p.get("auto_bid", b.get("auto_bid", False))
            })
    return pd.DataFrame(rows)


# ======================================================
# SIDEBAR – ADD BUYER
# ======================================================
st.sidebar.title("➕ Nouvel acheteur")

with st.sidebar.form("add_buyer_form"):
    buyer_name = st.text_input("Nom acheteur")
    auto_bid = st.checkbox("Auto-bid activé", value=True)

    buyer_products = {}
    can_submit = True

    for p in products:
        st.markdown(f"### {p['name']} ({p['id']})")

        # Prix minimum basé sur marché
        market_price = get_market_max_price(p["id"])
        min_price = market_price + 0.01 if market_price is not None else p["starting_price"]

        # Quantité initiale = multiple
        qty = st.number_input(
            "Quantité souhaitée",
            min_value=p["volume_multiple"],
            max_value=p["stock"],
            step=p["volume_multiple"],
            value=p["volume_multiple"]
        )

        # Vérifie si MOQ vendeur atteint
        if qty < p["seller_moq"]:
            st.warning(f"La quantité saisie pour {p['id']} doit être >= MOQ vendeur ({p['seller_moq']})")
            can_submit = False

        # Prix proposé >= marché
        current_price = st.number_input(
            "Prix proposé",
            min_value=min_price,
            value=min_price
        )

        # Prix max fixe
        max_price = st.number_input(
            "Prix max (plafond fixe)",
            min_value=current_price,
            value=current_price
        )

        buyer_products[p["id"]] = {
            "qty_desired": qty,
            "current_price": current_price,
            "max_price": max_price,
            "moq": p["seller_moq"]
        }

    submitted = st.form_submit_button("Ajouter l’acheteur", disabled=not can_submit)


# ======================================================
# Traitement après submit (hors form)
# ======================================================
if submitted and buyer_name:
    new_buyer = {
        "name": buyer_name,
        "products": buyer_products,
        "auto_bid": auto_bid
    }

    # --- Simulation de positionnement gagnant/perdant ---
    test_buyers = copy.deepcopy(st.session_state.buyers) + [new_buyer]
    alloc, _ = solve_model(test_buyers, products)
    won = any(alloc.get(buyer_name, {}).get(pid, 0) > 0 for pid in buyer_products)
    st.session_state.positioning = "🟢 GAGNANT" if won else "🔴 PERDANT"

    # --- Ajout réel et auto-bid ---
    st.session_state.buyers.append(new_buyer)
    st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)

    snapshot(f"Ajout acheteur {buyer_name}")

    st.success("Acheteur ajouté et auto-bid exécuté")


# ======================================================
# MAIN
# ======================================================
st.title("🧪 Interface de test – Allocation multi-acheteurs")

if st.session_state.positioning:
    st.subheader(f"Positionnement du dernier acheteur : {st.session_state.positioning}")

st.subheader("📦 Produits")
st.dataframe(pd.DataFrame(products), use_container_width=True)

st.subheader("👥 Acheteurs")
if st.session_state.buyers:
    st.dataframe(buyers_df(), use_container_width=True)
else:
    st.info("Aucun acheteur")


# ======================================================
# ACTIONS
# ======================================================
st.subheader("⚙️ Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶️ Allocation"):
        snapshot("Allocation manuelle")

with col2:
    if st.button("🤖 Auto-bid"):
        st.session_state.buyers = run_auto_bid_aggressive(st.session_state.buyers, products)
        snapshot("Auto-bid manuel")

with col3:
    if st.button("🧹 Reset"):
        st.session_state.buyers = []
        st.session_state.history = []
        st.session_state.positioning = None
        st.success("Données réinitialisées")


# ======================================================
# CURRENT ALLOCATION
# ======================================================
if st.session_state.history:
    last = st.session_state.history[-1]

    st.subheader("📊 Allocation actuelle")
    rows = []

    for b in last["buyers"]:
        for pid, qty in last["allocations"][b["name"]].items():
            price = b["products"][pid]["current_price"]
            rows.append({
                "Acheteur": b["name"],
                "Produit": pid,
                "Quantité": qty,
                "Prix": price,
                "CA": qty * price
            })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.metric("💰 CA total", f"{last['total_ca']:.2f} €")


# ======================================================
# HISTORY
# ======================================================
st.subheader("🕒 Historique")

if st.session_state.history:
    hist_df = pd.DataFrame([
        {
            "Itération": i,
            "Label": h["label"],
            "CA": h["total_ca"]
        }
        for i, h in enumerate(st.session_state.history)
    ])
    st.dataframe(hist_df, use_container_width=True)
