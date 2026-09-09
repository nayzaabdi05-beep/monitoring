import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# Konfigurasi Layout Halaman Menjadi Lebar
st.set_page_config(page_title="Sistem Monitoring PT Epsindo", layout="wide", page_icon="📊")

# --- HEADER UTAMA SISTEM ---
st.title("📊 Sistem Monitoring Bulanan")
st.markdown("### PT Epsindo Jaya Pratama Workshop Duri")
st.write("Silakan unggah laporan bulanan perusahaan di bawah ini untuk memproses data secara otomatis.")
st.markdown("---")

# --- AREA UTAMA: KOTAK UPLOAD FILE ---
col_up1, col_up2, col_up3 = st.columns([1, 2, 1])

with col_up2:
    uploaded_file = st.file_uploader(
        "📂 Tarik atau Pilih File Laporan Bulanan (.xlsx / .csv)", 
        type=["xlsx", "csv"],
        help="Format file harus berisikan kolom data Material Request"
    )

# Cek apakah file sudah diunggah ke sistem
if uploaded_file is not None:
    # --- MEMBACA DATA ---
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # --- PERBAIKAN TOTAL: MENGISI SEL KOSONG / MERGED CELL MENYELURUH ---
    df = df.ffill()
    # -------------------------------------------------------------------
    
    st.success("Berhasil! Laporan bulanan telah terbaca oleh sistem.")
    
    st.markdown("---")

    # --- PENGATURAN KATEGORI & FILTER INTERAKTIF DI DASHBOARD UTAMA ---
    st.subheader("⚙️ Kontrol, Pengaturan & Filter Data")
    
    # Tombol Popover Pengaturan Batas Hari Interaktif di Dashboard
    with st.popover("⚙️ Atur Format Batas Hari Kategori"):
        st.markdown("### 🎛️ Pengaturan Lead Time Interaktif")
        st.write("Tentukan batas maksimal hari untuk masing-masing kategori:")
        
        # Pengaturan batas hari yang sepenuhnya dinamis
        batas_cepat = st.number_input("Maks Hari 'Cepat'", min_value=0, max_value=5, value=0)
        batas_standar = st.number_input("Maks Hari 'Standar'", min_value=0, max_value=5, value=1)
        batas_lambat = st.number_input("Maks Hari 'Lambat'", min_value=0, max_value=10, value=3)
        # Nilai di atas batas_lambat otomatis menjadi 'Sangat Lambat'

    # --- 1. PEMBERSIHAN & PENGOLAHAN DATA ---
    # Mengisi missing value Qty dengan median
    if 'Qty' in df.columns:
        median_qty = df['Qty'].median()
        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(median_qty)
    
    # Hitung Jarak Waktu (Lead Time) otomatis
    if 'MR Date' in df.columns and 'Tgl Penyerahan' in df.columns:
        df['MR Date'] = pd.to_datetime(df['MR Date'], errors='coerce')
        df['Tgl Penyerahan'] = pd.to_datetime(df['Tgl Penyerahan'], errors='coerce')
        df['Lead_Time'] = (df['Tgl Penyerahan'] - df['MR Date']).dt.days
        
        # LOGIKA KATEGORI YANG MENGIKUTI INPUT DARI POPOVER SECARA DINAMIS
        def label_kategori(val):
            if pd.isna(val):
                return 'Tidak Valid'
            elif val <= batas_cepat:
                return 'Cepat'
            elif val <= batas_standar:
                return 'Standar'
            elif val <= batas_lambat:
                return 'Lambat'
            else:
                return 'Sangat Lambat'  # Nilai di atas batas lambat (misal lewat dari 3 hari) mutlak ke sini
                
        df['Kategori_Waktu'] = df['Lead_Time'].apply(label_kategori)

    st.markdown("---")
    
    # Layout Filter Berdampingan (Filter Kategori & Pencarian Kata Kunci)
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        st.subheader("🔍 Filter Kategori Waktu")
        semua_kategori = ['Cepat', 'Standar', 'Lambat', 'Sangat Lambat', 'Tidak Valid']
        status_opsi = [kat for kat in semua_kategori if kat in df['Kategori_Waktu'].unique()]

        selected_status = st.multiselect(
            "Pilih kategori yang ingin ditampilkan:",
            options=status_opsi,
            default=status_opsi
        )
    
    with col_f2:
        st.subheader("🔎 Pencarian Cepat")
        keyword = st.text_input("Cari berdasarkan teks/nomor (No. MR, Material, PIC, dll):", "")

    # Terapkan Filter Kategori
    df_filtered = df[df['Kategori_Waktu'].isin(selected_status)]

    # Terapkan Filter Pencarian Kata Kunci Jika Diisi
    if keyword:
        mask = df_filtered.astype(str).apply(lambda col: col.str.contains(keyword, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[mask]

    st.markdown("---")

    # --- 3. RINGKASAN KARTU METRIK OPERASIONAL (6 KOLOM LENGKAP) ---
    st.subheader("📈 Ringkasan Eksekutif Kinerja Gudang")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    
    total_req = len(df_filtered)
    max_lead = f"{df_filtered['Lead_Time'].max():.0f} Hari" if 'Lead_Time' in df_filtered.columns and not df_filtered.empty else "0 Hari"
    
    jml_cepat = len(df_filtered[df_filtered['Kategori_Waktu'] == 'Cepat']) if 'Kategori_Waktu' in df_filtered.columns else 0
    jml_standar = len(df_filtered[df_filtered['Kategori_Waktu'] == 'Standar']) if 'Kategori_Waktu' in df_filtered.columns else 0
    jml_lambat = len(df_filtered[df_filtered['Kategori_Waktu'] == 'Lambat']) if 'Kategori_Waktu' in df_filtered.columns else 0
    jml_sangat_lambat = len(df_filtered[df_filtered['Kategori_Waktu'] == 'Sangat Lambat']) if 'Kategori_Waktu' in df_filtered.columns else 0

    m1.metric("Total Data", total_req)
    m2.metric("Waktu Terlama", max_lead)
    m3.metric("🚀 Cepat", jml_cepat)
    m4.metric("⏱️ Standar", jml_standar)
    m5.metric("🐢 Lambat", jml_lambat)
    m6.metric("⚠️ Sangat Lambat", jml_sangat_lambat)
    
    # --- VISUALISASI GRAFIK INTERAKTIF ---
    if 'Kategori_Waktu' in df_filtered.columns and not df_filtered.empty:
        st.markdown("### 📊 Grafik Sebaran Kinerja Pengerjaan")
        chart_data = df_filtered['Kategori_Waktu'].value_counts().reset_index()
        chart_data.columns = ['Kategori', 'Jumlah']
        st.bar_chart(chart_data.set_index('Kategori'))

    st.markdown("---")

    # --- 4. TABEL DETAIL DATA & TOMBOL DOWNLOAD ---
    st.subheader("📋 Lembar Data Masuk (Database Viewer)")
    st.dataframe(df_filtered, use_container_width=True)

    # --- FUNGSI PEMBUATAN FILE EKSPOR ---
    col_dl1, col_dl2, col_dl3 = st.columns(3)

    # A. Tombol Download Excel (.xlsx)
    with col_dl1:
        output_excel = BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False, sheet_name='Laporan_Filtered')
        excel_data = output_excel.getvalue()

        st.download_button(
            label="📥 Unduh Data ke Excel (.xlsx)",
            data=excel_data,
            file_name="Laporan_Material_Request_Epsindo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    # Tampilan awal jika belum ada file yang di-upload
    st.info("ℹ️ **Petunjuk Penggunaan:** Silakan klik kotak unggah di atas atau tarik file laporan Excel/CSV perusahaan ke area tersebut untuk menampilkan sistem monitoring dan database viewer.")