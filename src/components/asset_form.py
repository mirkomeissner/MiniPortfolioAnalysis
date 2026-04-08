import streamlit as st
from src.database import get_ref_data, supabase

def asset_bulk_form():
    """Renders the bulk input form for new assets."""
    st.title("Create New Assets")
    
    # 1. Daten für Dropdowns laden
    ac_dict = get_ref_data("RefAssetClass")
    reg_dict = get_ref_data("RefRegion")
    sec_dict = get_ref_data("RefSector")
    ps_dict = get_ref_data("RefPriceSource")

    if all([ac_dict, reg_dict, sec_dict, ps_dict]):
        # 2. Tabellen-Header Layout
        header_cols = st.columns([1.5, 2, 0.8, 0.8, 1.5, 1.5, 1.5, 1.5, 0.5])
        headers = ["ISIN", "Name", "Ticker", "Curr", "PriceSource", "AssetClass", "Region", "Sector", ""]
        for col, label in zip(header_cols, headers):
            col.write(f"**{label}**")

        rows_to_delete = []
        
        # 3. Dynamische Zeilen-Generierung
        for idx, row in enumerate(st.session_state["rows"]):
            cols = st.columns([1.5, 2, 0.8, 0.8, 1.5, 1.5, 1.5, 1.5, 0.5])
            
            st.session_state["rows"][idx]["ISIN"] = cols[0].text_input("ISIN", value=row["ISIN"], key=f"isin_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["Name"] = cols[1].text_input("Name", value=row["Name"], key=f"name_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["Ticker"] = cols[2].text_input("Ticker", value=row["Ticker"], key=f"tick_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["Currency"] = cols[3].text_input("Curr", value=row["Currency"], key=f"curr_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["PriceSource"] = cols[4].selectbox("PS", options=list(ps_dict.keys()), key=f"ps_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["AssetClass"] = cols[5].selectbox("AC", options=list(ac_dict.keys()), key=f"ac_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["Region"] = cols[6].selectbox("Reg", options=list(reg_dict.keys()), key=f"reg_{idx}", label_visibility="collapsed")
            st.session_state["rows"][idx]["Sector"] = cols[7].selectbox("Sec", options=list(sec_dict.keys()), key=f"sec_{idx}", label_visibility="collapsed")
            
            if cols[8].button("🗑️", key=f"del_{idx}"):
                rows_to_delete.append(idx)

        # Zeilen löschen Logik
        if rows_to_delete:
            for i in reversed(rows_to_delete):
                st.session_state["rows"].pop(i)
            st.rerun()

        st.markdown("---")
        
        # 4. Buttons im Footer
        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 4])
        
        if btn_col1.button("➕ Add Row"):
            st.session_state["rows"].append({
                "ISIN": "", "Name": "", "Ticker": "", "Currency": "USD", 
                "PriceSource": "", "AssetClass": "", "Region": "", "Sector": ""
            })
            st.rerun()

        if btn_col2.button("🚀 Submit All", type="primary"):
            payload = []
            valid = True
            for r in st.session_state["rows"]:
                if not r["ISIN"] or not r["Name"]:
                    st.error("ISIN and Name are mandatory for all rows!")
                    valid = False
                    break
                
                payload.append({
                    "ISIN": r["ISIN"],
                    "Name": r["Name"],
                    "Ticker": r["Ticker"],
                    "Currency": r["Currency"],
                    "PriceSource": ps_dict[r["PriceSource"]],
                    "AssetClassCode": ac_dict[r["AssetClass"]],
                    "RegionCode": reg_dict[r["Region"]],
                    "SectorCode": sec_dict[r["Sector"]],
                    "created_by": st.session_state["user_name"]
                })
            
            if valid and payload:
                try:
                    supabase.table("AssetStaticData").insert(payload).execute()
                    st.success(f"✅ Successfully inserted {len(payload)} records!")
                    st.session_state["view"] = "list"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Database Error: {e}")
        
        if btn_col3.button("Cancel"):
            st.session_state["view"] = "list"
            st.rerun()
