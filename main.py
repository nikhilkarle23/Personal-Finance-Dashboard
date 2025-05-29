import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="Personal Finance Dashboard", page_icon="💰", layout="wide")

# Load or initialize budget
budget_file = "budgets.json"

if "budgets" not in st.session_state:
    st.session_state.budgets = {}

if os.path.exists(budget_file):
    with open(budget_file, "r") as f:
        st.session_state.budgets = json.load(f)

def save_budgets():
    with open(budget_file, "w") as f:
        json.dump(st.session_state.budgets, f)


# Load or initialize categories
category_file = "categories.json"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": [],
    }

if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)

def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f, indent=2)

# Categorize based on keywords
def categorize_transactions(df):
    df["Category"] = "Uncategorized"
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue
        for keyword in keywords:
            mask = df["Details"].str.contains(keyword, case=False, na=False)
            df.loc[mask, "Category"] = category
    return df

# Load CSV or Excel
def load_transactions(file):
    try:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        df.columns = [col.strip() for col in df.columns]
        df["Amount"] = df["Amount"].astype(str).str.replace(",", "").astype(float)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
        df = categorize_transactions(df)
        return df
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None

# Add new keyword to category
def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False

# Main app UI
def main():
    st.title("📊 Personal Finance Dashboard")

    uploaded_file = st.file_uploader("Upload your bank statement (.csv or .xlsx)", type=["csv", "xlsx"])

    if uploaded_file is not None:
        df = load_transactions(uploaded_file)

        if df is not None:
            debits_df = df[df["Debit/Credit"].str.lower() == "debit"].copy()
            credits_df = df[df["Debit/Credit"].str.lower() == "credit"].copy()
            st.session_state.debits_df = debits_df.copy()

            tab1, tab2, tab3 = st.tabs(["🧾 Expenses (Debits)", "💸 Payments (Credits)", "⚙️ Budget & Category Setup"])

            with tab1:
                st.subheader("📋 Category-wise Expense Summary")
                category_totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
                category_totals = category_totals.sort_values("Amount", ascending=False)

                st.dataframe(
                    category_totals,
                    column_config={"Amount": st.column_config.NumberColumn("Amount", format="%.2f INR")},
                    use_container_width=True,
                    hide_index=True
                )

                fig = px.pie(category_totals, values="Amount", names="Category", title="💸 Expenses by Category")
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Category-wise Spending Trend Over Time")

                # Prepare data for time-based trend
                st.session_state.debits_df["Month"] = st.session_state.debits_df["Date"].dt.to_period("M").astype(str)

                monthly_category_trend = (
                    st.session_state.debits_df
                    .groupby(["Month", "Category"])["Amount"]
                    .sum()
                    .reset_index()
                )

                fig_bar = px.bar(
                    monthly_category_trend,
                    x="Month",
                    y="Amount",
                    color="Category",
                    title="Monthly Spending by Category",
                    barmode="stack"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

                if "debits_df" in st.session_state:
                    st.markdown("### 📈 Budget vs Actual (This Month)")
                    
                    # Get the current month in YYYY-MM format
                    # this_month = pd.Timestamp.now().to_period("M").strftime("%Y-%m")
                    
                    # Filter debit entries for the current month
                    # df_month = st.session_state.debits_df[
                    #     st.session_state.debits_df["Date"].dt.to_period("M").astype(str) == this_month
                    # ]
                    
                    # Group actual spending by category
                    actuals_dict = st.session_state.debits_df.groupby("Category")["Amount"].sum().to_dict()

                    # Build comparison table
                    budget_vs_actual = pd.DataFrame([
                        {
                            "Category": cat,
                            "Budget (INR)": st.session_state.budgets.get(cat, 0),
                            "Actual Spend (INR)": actuals_dict.get(cat, 0)
                        }
                        for cat in st.session_state.categories.keys()
                        if cat != "Uncategorized"
                    ])

                    # Calculate difference
                    budget_vs_actual["Difference"] = (
                        budget_vs_actual["Budget (INR)"] - budget_vs_actual["Actual Spend (INR)"]
                    )

                    # Show as table
                    st.dataframe(budget_vs_actual, use_container_width=True)


            with tab2:
                st.subheader("💳 Payments Summary")
                total_credits = credits_df["Amount"].sum()
                st.metric("Total Credits", f"{total_credits:,.2f} INR")
                st.dataframe(credits_df, use_container_width=True)

            with tab3:
                st.subheader("⚙️ Budget & Category Setup")

                with st.expander("📅 Set Monthly Budgets", expanded=True):
                    budget_cols = st.columns(2)
                    for i, category in enumerate(st.session_state.categories.keys()):
                        if category == "Uncategorized":
                            continue
                        col = budget_cols[i % 2]
                        with col:
                            current_budget = st.session_state.budgets.get(category, 0)
                            new_budget = st.number_input(
                                f"{category} Budget (INR)",
                                min_value=0.0,
                                value=float(current_budget),
                                step=100.0,
                                key=f"budget_input_{category}"
                            )
                            st.session_state.budgets[category] = new_budget

                    if st.button("💾 Save Budgets"):
                        save_budgets()
                        st.success("Budgets saved successfully!")

                st.markdown("---")

                with st.expander("📁 Manage Categories & Keywords", expanded=True):
                    left_col, right_col = st.columns([2, 1])

                    with left_col:
                        st.markdown("### 📋 Existing Categories & Keywords")
                        for category, keywords in st.session_state.categories.items():
                            st.markdown(f"#### 🔹 {category}")
                            if keywords:
                                for keyword in keywords:
                                    col1, col2 = st.columns([5, 1])
                                    col1.markdown(f"- {keyword}")
                                    if col2.button("❌", key=f"del_{category}_{keyword}"):
                                        st.session_state.categories[category].remove(keyword)
                                        save_categories()
                                        st.experimental_rerun()
                            else:
                                st.markdown("*No keywords assigned yet.*")
                            st.markdown("---")


                    with right_col:
                        st.markdown("### ➕ Add New Category")
                        new_category = st.text_input("Category Name")
                        if st.button("Add Category"):
                            if new_category and new_category not in st.session_state.categories:
                                st.session_state.categories[new_category] = []
                                save_categories()
                                st.success(f"Category '{new_category}' added!")
                                st.experimental_rerun()

                        st.markdown("### ➕ Add Keyword to Existing Category")
                        keyword_category = st.selectbox("Select Category", list(st.session_state.categories.keys()))
                        new_keyword = st.text_input("Keyword")
                        if st.button("Add Keyword"):
                            if add_keyword_to_category(keyword_category, new_keyword):
                                st.success(f"Keyword '{new_keyword}' added to '{keyword_category}'")
                            else:
                                st.warning("Keyword already exists or invalid.")

main()
