import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# Konfigurasi Layout Halaman Menjadi Lebar
st.set_page_config(page_title="Sistem Monitoring PT Epsindo", layout="wide")

# --- HEADER UTAMA SISTEM ---
st.title("Sistem Monitoring Bulanan")
st.markdown("### PT Epsindo Jaya Pratama Workshop Duri")
st.write("Silakan unggah laporan bulanan perusahaan di bawah ini untuk memproses data secara otomatis.")
st.markdown("---")

# --- AREA UTAMA: KOTAK UPLOAD FILE ---
col_up1, col_up2, col_up3 = st.columns([1, 2, 1])

with col_up2:
    uploaded_file = st.file_uploader(
        "Tarik atau Pilih File Laporan Bulanan (.xlsx / .csv)", 
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
    
    # --- 1. PEMBERSIHAN & PENGOLAHAN DATA ---
    # Mengisi missing value Qty dengan median (sesuai revisi penguji)
    if 'Qty' in df.columns:
        median_qty = df['Qty'].median()
        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(median_qty)
    
    # Hitung Jarak Waktu (Lead Time) otomatis
    if 'MR Date' in df.columns and 'Tgl Penyerahan' in df.columns:
        df['MR Date'] = pd.to_datetime(df['MR Date'], errors='coerce')
        df['Tgl Penyerahan'] = pd.to_datetime(df['Tgl Penyerahan'], errors='coerce')
        df['Lead_Time'] = (df['Tgl Penyerahan'] - df['MR Date']).dt.days
        
        def label_kategori(val):
            if pd.isna(val):
                return 'Tidak Valid'
            elif val <= 1:
                return 'Cepat'
            elif val <= 3:
                return 'Standar'
            else:
                return 'Lambat'
        df['Kategori_Waktu'] = df['Lead_Time'].apply(label_kategori)

    st.markdown("---")

    # --- 2. MENU FILTER INTERAKTIF DI DASHBOARD UTAMA ---
    st.subheader("Filter & Kontrol Data")
    if 'Kategori_Waktu' in df.columns:
        status_opsi = df['Kategori_Waktu'].unique()
        selected_status = st.multiselect(
            "Filter berdasarkan Kategori Waktu Pengerjaan:",
            options=status_opsi,
            default=list(status_opsi)
        )
        df_filtered = df[df['Kategori_Waktu'].isin(selected_status)]
    else:
        df_filtered = df

    st.markdown("---")

    # --- 3. RINGKASAN KARTU METRIK OPERASIONAL ---
    st.subheader("Ringkasan Eksekutif Kinerja Gudang")
    m1, m2, m3, m4 = st.columns(4)
    total_req = len(df_filtered)
    max_lead = f"{df_filtered['Lead_Time'].max():.0f} Hari" if 'Lead_Time' in df_filtered.columns else "N/A"
    jml_lambat = len(df_filtered[df_filtered['Kategori_Waktu'] == 'Lambat']) if 'Kategori_Waktu' in df_filtered.columns else 0
    jml_cepat = len(df_filtered[df_filtered['Kategori_Waktu'] == 'Cepat']) if 'Kategori_Waktu' in df_filtered.columns else 0

    m1.metric("Total Permintaan (MR)", total_req)
    m2.metric("Waktu Terlama", max_lead)
    m3.metric("Kategori 'Lambat'", jml_lambat)
    m4.metric("Kategori 'Cepat'", jml_cepat)
    
    st.markdown("---")

    # --- 4. TABEL DETAIL DATA & TOMBOL DOWNLOAD ---
    st.subheader("Lembar Data Masuk (Database Viewer)")
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
            label=" Unduh Data ke Excel (.xlsx)",
            data=excel_data,
            file_name="Laporan_Material_Request_Epsindo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    # Tampilan awal jika belum ada file yang di-upload
    st.info("**Petunjuk Penggunaan:** Silakan klik kotak unggah di atas atau tarik file laporan Excel/CSV perusahaan ke area tersebut untuk menampilkan sistem monitoring dan database viewer.")