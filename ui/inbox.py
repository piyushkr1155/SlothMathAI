"""Lazy Inbox view for SlothMate AI."""
import streamlit as st
from pathlib import Path
import shutil
from storage.database import Database
from services.inbox_processor import InboxProcessor
from processors.text_reader import compute_file_hash
from config import config

def render_inbox(db: Database, processor: InboxProcessor):
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <h2 style="margin: 0; color: #1E3A1A;">📁 Lazy Inbox</h2>
            <p style="margin: 4px 0 0 0; color: #5A6B54;">
                Drop notes, meeting minutes, and PDFs. SlothMate processes them locally and privately.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # File Upload Widget
    col_upload, col_sample = st.columns([2, 1])
    with col_upload:
        uploaded_files = st.file_uploader(
            "Upload documents (.txt, .md, .pdf)",
            type=["txt", "md", "pdf"],
            accept_multiple_files=True,
            help="Files are stored strictly in your local inbox directory."
        )

        if uploaded_files:
            saved_count = 0
            for uploaded_file in uploaded_files:
                target_path = processor.inbox_dir / uploaded_file.name
                
                # Check size limit
                if uploaded_file.size > processor.max_file_size_bytes:
                    max_mb = processor.max_file_size_bytes / (1024 * 1024)
                    st.error(f"'{uploaded_file.name}' exceeds the maximum allowed file size of {max_mb:.0f} MB.")
                    continue

                with open(target_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                saved_count += 1

            if saved_count > 0:
                st.success(f"Saved {saved_count} file(s) into your local inbox!")
                st.rerun()

    with col_sample:
        st.markdown("**Need test files?**")
        st.caption("Load realistic fictional sample notes and roadmap documents.")
        if st.button("📥 Load Sample Documents", use_container_width=True):
            sample_dir = Path(__file__).resolve().parent.parent / "sample_data"
            loaded = 0
            if sample_dir.exists():
                for sf in sample_dir.iterdir():
                    if sf.is_file() and sf.suffix.lower() in config.supported_extensions:
                        dest = processor.inbox_dir / sf.name
                        shutil.copy2(sf, dest)
                        loaded += 1
            if loaded > 0:
                st.success(f"Copied {loaded} sample files to inbox!")
                st.rerun()
            else:
                st.warning("No sample files found in sample_data/ directory.")

    st.markdown("<hr style='margin: 20px 0; border: none; border-top: 1px solid #E2E8DE;' />", unsafe_allow_html=True)

    # Inbox Directory Content Listing
    inbox_files = processor.scan_inbox()
    st.markdown(f"### 📂 Documents in Inbox ({len(inbox_files)})")
    st.caption(f"Location: `{processor.inbox_dir.resolve()}`")

    if not inbox_files:
        st.info("The inbox is currently empty. Upload files above or place them in your inbox directory.")
        return

    # Table of files
    for file_path in inbox_files:
        size_kb = file_path.stat().st_size / 1024
        try:
            f_hash = compute_file_hash(file_path)
            doc_record = db.get_document_by_hash(f_hash)
        except Exception:
            f_hash = "unknown"
            doc_record = None

        status = doc_record.get("status") if doc_record else "pending"
        
        # Color badge for status
        if status == "processed":
            status_badge = "🟢 Processed"
        elif status == "failed":
            status_badge = "🔴 Failed"
        else:
            status_badge = "🟡 Pending"

        with st.container():
            col_f1, col_f2, col_f3, col_f4 = st.columns([2.5, 1, 1, 1.2])
            with col_f1:
                st.markdown(f"**{file_path.name}**")
                st.caption(f"Type: `{file_path.suffix}` | Size: `{size_kb:.1f} KB` | Hash: `{f_hash[:8]}...`")
            with col_f2:
                st.markdown(f"**{status_badge}**")
            with col_f3:
                if st.button("⚡ Process", key=f"proc_{file_path.name}", help="Process only this document"):
                    with st.spinner(f"Processing {file_path.name}..."):
                        res = processor.process_single_file(file_path, force_reprocess=True)
                        if res.get("status") == "processed":
                            st.success(f"Processed '{file_path.name}' ({res.get('tasks_count', 0)} tasks extracted).")
                        else:
                            st.error(f"Error processing '{file_path.name}': {res.get('error')}")
                        st.rerun()
            with col_f4:
                if st.button("🗑️ Delete", key=f"del_{file_path.name}", help="Remove from local inbox"):
                    try:
                        file_path.unlink()
                        if doc_record:
                            db.delete_document(doc_record["id"])
                        st.success(f"Removed '{file_path.name}'")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not delete: {str(e)}")

            if doc_record and doc_record.get("summary"):
                with st.expander(f"📄 View summary for {file_path.name}"):
                    st.markdown(f"**Summary:** {doc_record['summary']}")
                    if doc_record.get("key_points"):
                        st.markdown("**Key Points:**")
                        kp = doc_record["key_points"]
                        if isinstance(kp, str):
                            try:
                                import json
                                kp = json.loads(kp)
                            except Exception:
                                kp = [kp]
                        for p in kp:
                            st.markdown(f"- {p}")

            if doc_record and doc_record.get("error_message"):
                st.error(f"**Error Details:** {doc_record['error_message']}")

            st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px dashed #E2E8DE;' />", unsafe_allow_html=True)
