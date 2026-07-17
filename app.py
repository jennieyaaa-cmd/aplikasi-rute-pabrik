import streamlit as st
import pandas as pd
import gurobipy as gp
from gurobipy import GRB

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.set_page_config(page_title="Login Sisfo Rute", page_icon="🔐", layout="centered")
    st.title("🔐 Sistem Informasi Optimasi Rute Pabrik")
    st.write("Silakan masukkan akun operasional pabrik:")
    
    username = st.text_input("Username", value="pabriksukses")
    password = st.text_input("Password", type="090626")
    
    if st.button("Login Masuk", type="primary"):
        
        if username == "pabriksukses" and password == "090626":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Username atau Password salah! Hubungi Admin Sistem.")
    st.stop()
 

st.set_page_config(page_title="Dashboard Rute Distribusi", page_icon="🚚", layout="wide")
st.title("🚚 Dashboard Optimasi Rute Distribusi (MILP-Gurobi)")
st.subheader("Sistem Pendukung Keputusan Penjadwalan Armada Harian")

with st.sidebar:
    st.markdown("### 👤 Karyawan Aktif")
    st.info("pabrikr12@gmail.com")
    st.success("🔑 Lisensi Gurobi WLS Aktif")
    if st.button("Log Out / Keluar"):
        st.session_state["authenticated"] = False
        st.rerun()

st.markdown("### ⚙️ Parameter Input Operasional")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### ⏱️ Waktu Proses (Menit)")
    t_pabrik = st.number_input("Waktu Muat di Pabrik (t_pabrik)", min_value=0, value=10)
    t_retailer = st.number_input("Waktu Bongkar di Toko (t_retailer)", min_value=0, value=10)
    T_max = st.number_input("Batas Kerja Maksimal (T_max)", min_value=60, value=450)

with col2:
    st.markdown("#### 📦 Kapasitas Armada (Keranjang)")
    cap_mobil1 = st.number_input("Kapasitas Kendaraan 1", min_value=1, value=20)
    cap_mobil2 = st.number_input("Kapasitas Kendaraan 2", min_value=1, value=25)

with col3:
    st.markdown("#### 🛠️ Pengaturan Gurobi")
    time_limit = st.number_input("Batas Waktu Komputasi (detik)", min_value=5, value=30)
    M_big = st.number_input("Nilai Konstanta M (Big M)", min_value=1000, value=10000)

st.divider()

st.markdown("### 🎯 Jumlah Demand Keranjang Toko (Retailer 1 - 20)")
st.write("Silakan ganti nilai di dalam tabel di bawah ini sesuai pesanan hari ini:")

default_demand = {
    f"R{i}": [3 if i in [1, 2, 11, 12, 16, 17] else 4 if i == 5 else 2] 
    for i in range(1, 21)
}
df_demand = pd.DataFrame(default_demand)
edited_demand = st.data_editor(df_demand, hide_index=True)
total_demand = edited_demand.sum().sum()

st.write(f"Total Muatan Hari Ini: **{total_demand} keranjang** | Total Kapasitas Mobil: **{cap_mobil1 + cap_mobil2} keranjang**")

st.divider()

st.markdown("### 🗺️ Matriks Waktu Perjalanan Antar Lokasi (Menit)")
st.write("Baris/Kolom 0 = Pabrik, Baris/Kolom 1-20 = Retailer 1-20. Ubah sel jika waktu jalan berubah:")

default_matrix = []
for i in range(21):
    row = []
    for j in range(21):
        if i == j:
            row.append(999999.0 if i > 0 else 0.0)
        else:
            row.append(15.0)
    default_matrix.append(row)

df_matrix = pd.DataFrame(default_matrix, 
                         columns=[f"L{i}" for i in range(21)], 
                         index=[f"L{i}" for i in range(21)])
edited_matrix = st.data_editor(df_matrix)

st.divider()

if st.button("🚀 PROSES OPTIMALISASI RUTE PABRIK", type="primary"):
    V = list(range(1, 21))
    K = [1, 2]
    Q = {1: cap_mobil1, 2: cap_mobil2}
    current_demand = {i: int(edited_demand.iloc[0, i-1]) for i in V}
    
    t_input = {}
    matrix_values = edited_matrix.values.tolist()
    for i in range(21):
        for j in range(21):
            t_input[i, j] = float(matrix_values[i][j])
            
    with st.spinner("Sedang menjalankan kalkulasi Gurobi..."):
        try:
            params = {
                "WLSACCESSID": "AKU_AKAN_BANTU_AMANKAN_INI", 
                "WLSSECRET": "SECRET_KAMU",   
                "LICENSEID": 2818118,
            }
            
            env = gp.Env(params=params)
            model = gp.Model("MTVRP_Direct_Dashboard", env=env)
            
            model.setParam('TimeLimit', time_limit)
            model.setParam('OutputFlag', 0)
            
            x = model.addVars([(i, j, k) for i in V for j in V if i != j for k in K], vtype=GRB.BINARY, name="x")
            x_refill = model.addVars([(i, j, k) for i in V for j in V if i != j for k in K], vtype=GRB.BINARY, name="x_refill")
            start = model.addVars(V, K, vtype=GRB.BINARY, name="start")
            end = model.addVars(V, K, vtype=GRB.BINARY, name="end")
            W = model.addVars(V, K, vtype=GRB.CONTINUOUS, lb=0, name="W")
            Y = model.addVars(V, K, vtype=GRB.CONTINUOUS, lb=0, name="Y")
            
            for i in V:
                for k in K:
                    Y[i, k].ub = Q[k] - current_demand[i]
                    
            model.setObjective(
                gp.quicksum((t_input[i, j] + t_retailer) * x[i, j, k] for i in V for j in V if i != j for k in K) +
                gp.quicksum((t_input[i, 0] + t_pabrik + t_input[0, j] + t_retailer) * x_refill[i, j, k] for i in V for j in V if i != j for k in K) +
                gp.quicksum((t_pabrik + t_input[0, i]) * start[i, k] for i in V for k in K) +
                gp.quicksum(t_input[i, 0] * end[i, k] for i in V for k in K),
                GRB.MINIMIZE
            )
            
            model.addConstrs(gp.quicksum(x[i, j, k] + x_refill[i, j, k] for i in V if i != j for k in K) + gp.quicksum(start[j, k] for k in K) == 1 for j in V)
            model.addConstrs(gp.quicksum(x[i, j, k] + x_refill[i, j, k] for i in V if i != j) + start[j, k] == gp.quicksum(x[j, l, k] + x_refill[j, l, k] for l in V if j != l) + end[j, k] for j in V for k in K)
            model.addConstrs(gp.quicksum(start[i, k] for i in V) <= 1 for k in K)
            model.addConstrs(gp.quicksum(end[i, k] for i in V) <= 1 for k in K)
            model.addConstrs(Y[i, k] <= Q[k] - current_demand[i] + M_big * (1 - start[i, k]) for i in V for k in K)
            model.addConstrs(Y[j, k] <= Y[i, k] - current_demand[j] + M_big * (1 - x[i, j, k]) for i in V for j in V if i != j for k in K)
            model.addConstrs(W[i, k] >= t_pabrik + t_input[0, i] - M_big * (1 - start[i, k]) for i in V for k in K)
            model.addConstrs(W[j, k] >= W[i, k] + t_retailer + t_input[i, j] * x[i, j, k] + (t_input[i, 0] + t_pabrik + t_input[0, j]) * x_refill[i, j, k] - M_big * (2 - x[i, j, k] - x_refill[i, j, k]) for i in V for j in V if i != j for k in K)
            model.addConstrs(W[i, k] + t_retailer + t_input[i, 0] <= T_max + M_big * (1 - end[i, k]) for i in V for k in K)
            
            model.optimize()
            
            if model.status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
                st.success("🎉 OPTIMASI SELESAI & BERHASIL DITEMUKAN!")
                st.metric(label="Total Waktu Operasional Armada", value=f"{round(model.ObjVal, 2)} Menit")
                
                for k in K:
                    start_node = next((i for i in V if start[i, k].x > 0.5), None)
                    if start_node is not None:
                        route_text = f"Pabrik ➡️ R-{start_node}"
                        curr = start_node
                        while True:
                            nxt_direct = next((j for j in V if curr != j and (curr, j, k) in x and x[curr, j, k].x > 0.5), None)
                            nxt_refill = next((j for j in V if curr != j and (curr, j, k) in x_refill and x_refill[curr, j, k].x > 0.5), None)
                            
                            if nxt_direct is not None:
                                route_text += f" ➡️ R-{nxt_direct}"
                                curr = nxt_direct
                            elif nxt_refill is not None:
                                route_text += f" 🔄 **[REFILL KE PABRIK]** ➡️ Pabrik ➡️ R-{nxt_refill}"
                                curr = nxt_refill
                            else:
                                break
                        route_text += " ➡️ Pabrik (Selesai)🏁"
                        st.info(f"**Rute Kendaraan {k} (Kapasitas {Q[k]}):**  \n{route_text}")
                    else:
                        st.warning(f"**Kendaraan {k}:** Tidak digunakan untuk pengiriman hari ini.")
            else:
                st.error("❌ Solusi Tidak Ditemukan (Infeasible).")
        except Exception as e:
            st.error(f"Gagal menjalankan kalkulasi: {str(e)}")
