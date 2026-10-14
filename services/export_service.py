from datetime import datetime
import io
from typing import List
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from core.database.models import TransactionRecord


class ExcelExportService:
    """
    Generates styled, professional Excel spreadsheets for personal financial reporting.
    Produces a summary dashboard tab and a detailed transaction history tab.
    """

    def generate_user_finance_workbook(
        self,
        user_name: str,
        transactions: List[TransactionRecord],
    ) -> io.BytesIO:
        """
        Builds and styles an Excel workbook containing:
        1. 'Resumen Financiero': Totals, KPIs, and category breakdown.
        2. 'Detalle de Movimientos': Filterable, formatted list of all transactions.
        Returns an in-memory BytesIO buffer ready for transmission.
        """
        wb = Workbook()

        # Styles definition
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=16, bold=True, color="1E293B")
        subtitle_font = Font(name="Calibri", size=10, italic=True, color="64748B")
        bold_font = Font(name="Calibri", size=11, bold=True, color="1E293B")
        regular_font = Font(name="Calibri", size=11, color="0F172A")

        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0"),
        )
        total_border = Border(
            top=Side(style="thin", color="94A3B8"),
            bottom=Side(style="double", color="1E293B"),
        )

        # ----------------------------------------------------
        # 1. Sheet 1: Resumen Financiero
        # ----------------------------------------------------
        ws_summary = wb.active
        ws_summary.title = "Resumen Financiero"
        ws_summary.views.sheetView[0].showGridLines = True

        # Header Title
        ws_summary["B2"] = "📊 REPORTE DE FINANZAS PERSONALES"
        ws_summary["B2"].font = title_font

        emission_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        ws_summary["B3"] = f"Usuario: {user_name}  |  Fecha de emisión: {emission_date}"
        ws_summary["B3"].font = subtitle_font

        # Calculate KPIs
        total_income = sum(tx.amount for tx in transactions if tx.transaction_type == "Ingreso")
        total_expenses = sum(tx.amount for tx in transactions if tx.transaction_type == "Gasto")
        net_balance = total_income - total_expenses
        total_transfers = sum(tx.amount for tx in transactions if tx.transaction_type == "Traspaso")

        # KPI Cards (Row 5 & 6)
        kpi_configs = [
            ("TOTAL INGRESOS", total_income, "B", "DCFCE7", "166534", "15803D"),
            ("TOTAL GASTOS", total_expenses, "C", "FEE2E2", "991B1B", "B91C1C"),
            ("BALANCE NETO", net_balance, "D", "DBEAFE", "1E40AF", "1D4ED8"),
            ("TRASPASOS", total_transfers, "E", "F1F5F9", "334155", "475569"),
        ]

        for label, val, col, bg_color, text_color, label_color in kpi_configs:
            lbl_cell = ws_summary[f"{col}5"]
            lbl_cell.value = label
            lbl_cell.font = Font(name="Calibri", size=9, bold=True, color=label_color)
            lbl_cell.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
            lbl_cell.alignment = Alignment(horizontal="center", vertical="center")

            val_cell = ws_summary[f"{col}6"]
            val_cell.value = val
            val_cell.font = Font(name="Calibri", size=13, bold=True, color=text_color)
            val_cell.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
            val_cell.alignment = Alignment(horizontal="center", vertical="center")
            val_cell.number_format = "$#,##0.00"

        ws_summary.row_dimensions[5].height = 20
        ws_summary.row_dimensions[6].height = 26

        # Category Breakdown Table (Row 9)
        ws_summary["B9"] = "DESGLOSE DE GASTOS POR CATEGORÍA"
        ws_summary["B9"].font = Font(name="Calibri", size=12, bold=True, color="1E293B")

        cat_headers = ["Categoría", "Monto Gastado", "% del Total", "Transacciones"]
        for idx, header in enumerate(cat_headers, start=2):
            col_letter = get_column_letter(idx)
            cell = ws_summary[f"{col_letter}10"]
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center" if idx > 2 else "left", vertical="center")

        ws_summary.row_dimensions[10].height = 24

        # Group expenses by category
        category_stats = {}
        for tx in transactions:
            if tx.transaction_type == "Gasto":
                cat = tx.category or "Otros"
                if cat not in category_stats:
                    category_stats[cat] = {"amount": 0.0, "count": 0}
                category_stats[cat]["amount"] += tx.amount
                category_stats[cat]["count"] += 1

        # Sort categories by amount descending
        sorted_categories = sorted(category_stats.items(), key=lambda item: item[1]["amount"], reverse=True)

        current_row = 11
        for cat_name, stats in sorted_categories:
            amount = stats["amount"]
            count = stats["count"]
            pct = (amount / total_expenses) if total_expenses > 0 else 0.0

            row_fill = PatternFill(start_color="F8FAFC" if current_row % 2 == 0 else "FFFFFF", fill_type="solid")

            # Col B: Categoría
            c_cat = ws_summary[f"B{current_row}"]
            c_cat.value = cat_name
            c_cat.font = regular_font
            c_cat.fill = row_fill
            c_cat.border = thin_border

            # Col C: Monto
            c_amt = ws_summary[f"C{current_row}"]
            c_amt.value = amount
            c_amt.font = regular_font
            c_amt.fill = row_fill
            c_amt.alignment = Alignment(horizontal="right", vertical="center")
            c_amt.number_format = "$#,##0.00"
            c_amt.border = thin_border

            # Col D: % del Total
            c_pct = ws_summary[f"D{current_row}"]
            c_pct.value = pct
            c_pct.font = regular_font
            c_pct.fill = row_fill
            c_pct.alignment = Alignment(horizontal="right", vertical="center")
            c_pct.number_format = "0.0%"
            c_pct.border = thin_border

            # Col E: Transacciones
            c_cnt = ws_summary[f"E{current_row}"]
            c_cnt.value = count
            c_cnt.font = regular_font
            c_cnt.fill = row_fill
            c_cnt.alignment = Alignment(horizontal="center", vertical="center")
            c_cnt.border = thin_border

            ws_summary.row_dimensions[current_row].height = 20
            current_row += 1

        # Total Row for Category Table
        tot_label = ws_summary[f"B{current_row}"]
        tot_label.value = "TOTAL GASTOS"
        tot_label.font = bold_font
        tot_label.border = total_border

        tot_amt = ws_summary[f"C{current_row}"]
        tot_amt.value = total_expenses
        tot_amt.font = bold_font
        tot_amt.alignment = Alignment(horizontal="right", vertical="center")
        tot_amt.number_format = "$#,##0.00"
        tot_amt.border = total_border

        tot_pct = ws_summary[f"D{current_row}"]
        tot_pct.value = 1.0 if total_expenses > 0 else 0.0
        tot_pct.font = bold_font
        tot_pct.alignment = Alignment(horizontal="right", vertical="center")
        tot_pct.number_format = "0.0%"
        tot_pct.border = total_border

        tot_cnt = ws_summary[f"E{current_row}"]
        tot_cnt.value = sum(s["count"] for s in category_stats.values())
        tot_cnt.font = bold_font
        tot_cnt.alignment = Alignment(horizontal="center", vertical="center")
        tot_cnt.border = total_border

        ws_summary.row_dimensions[current_row].height = 22

        # Adjust summary column widths
        ws_summary.column_dimensions["A"].width = 4
        ws_summary.column_dimensions["B"].width = 30
        ws_summary.column_dimensions["C"].width = 20
        ws_summary.column_dimensions["D"].width = 16
        ws_summary.column_dimensions["E"].width = 18

        # ----------------------------------------------------
        # 2. Sheet 2: Detalle de Movimientos
        # ----------------------------------------------------
        ws_detail = wb.create_sheet(title="Detalle de Movimientos")
        ws_detail.views.sheetView[0].showGridLines = True

        detail_headers = [
            "#",
            "Fecha",
            "Tipo",
            "Monto",
            "Categoría",
            "Subcategoría",
            "Cuenta Origen",
            "Cuenta Destino",
            "Descripción",
        ]

        for col_idx, header in enumerate(detail_headers, start=1):
            cell = ws_detail.cell(row=1, column=col_idx, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws_detail.row_dimensions[1].height = 26

        type_styles = {
            "Ingreso": {"font_color": "15803D", "bg_color": "DCFCE7"},
            "Gasto": {"font_color": "B91C1C", "bg_color": "FEE2E2"},
            "Traspaso": {"font_color": "1D4ED8", "bg_color": "DBEAFE"},
        }

        # Populate transaction rows
        for row_idx, tx in enumerate(transactions, start=2):
            is_even = row_idx % 2 == 0
            base_bg = "F8FAFC" if is_even else "FFFFFF"
            base_fill = PatternFill(start_color=base_bg, end_color=base_bg, fill_type="solid")

            # Col 1: #
            c1 = ws_detail.cell(row=row_idx, column=1, value=row_idx - 1)
            c1.alignment = Alignment(horizontal="center", vertical="center")
            c1.font = regular_font
            c1.fill = base_fill
            c1.border = thin_border

            # Col 2: Fecha
            c2 = ws_detail.cell(row=row_idx, column=2, value=tx.date.strftime("%Y-%m-%d"))
            c2.alignment = Alignment(horizontal="center", vertical="center")
            c2.font = regular_font
            c2.fill = base_fill
            c2.border = thin_border

            # Col 3: Tipo
            c3 = ws_detail.cell(row=row_idx, column=3, value=tx.transaction_type)
            c3.alignment = Alignment(horizontal="center", vertical="center")
            type_cfg = type_styles.get(tx.transaction_type, {"font_color": "0F172A", "bg_color": base_bg})
            c3.font = Font(name="Calibri", size=11, bold=True, color=type_cfg["font_color"])
            c3.fill = PatternFill(start_color=type_cfg["bg_color"], end_color=type_cfg["bg_color"], fill_type="solid")
            c3.border = thin_border

            # Col 4: Monto
            c4 = ws_detail.cell(row=row_idx, column=4, value=float(tx.amount))
            c4.alignment = Alignment(horizontal="right", vertical="center")
            c4.font = Font(name="Calibri", size=11, bold=True, color="0F172A")
            c4.number_format = "$#,##0.00"
            c4.fill = base_fill
            c4.border = thin_border

            # Col 5: Categoría
            c5 = ws_detail.cell(row=row_idx, column=5, value=tx.category or "")
            c5.font = regular_font
            c5.fill = base_fill
            c5.border = thin_border

            # Col 6: Subcategoría
            c6 = ws_detail.cell(row=row_idx, column=6, value=tx.subcategory or "")
            c6.font = regular_font
            c6.fill = base_fill
            c6.border = thin_border

            # Col 7: Cuenta Origen
            c7 = ws_detail.cell(row=row_idx, column=7, value=tx.source_account_name or "N/A")
            c7.font = regular_font
            c7.fill = base_fill
            c7.border = thin_border

            # Col 8: Cuenta Destino
            c8 = ws_detail.cell(row=row_idx, column=8, value=tx.destination_account_name or "N/A")
            c8.font = regular_font
            c8.fill = base_fill
            c8.border = thin_border

            # Col 9: Descripción
            c9 = ws_detail.cell(row=row_idx, column=9, value=tx.description or "")
            c9.font = regular_font
            c9.fill = base_fill
            c9.border = thin_border

            ws_detail.row_dimensions[row_idx].height = 20

        # Enable auto-filters and freeze panes
        last_row = max(len(transactions) + 1, 2)
        ws_detail.auto_filter.ref = f"A1:I{last_row}"
        ws_detail.freeze_panes = "A2"

        # Auto-adjust column widths for Detail sheet
        col_widths = {
            1: 6,   # #
            2: 14,  # Fecha
            3: 14,  # Tipo
            4: 16,  # Monto
            5: 24,  # Categoría
            6: 22,  # Subcategoría
            7: 24,  # Cuenta Origen
            8: 24,  # Cuenta Destino
            9: 36,  # Descripción
        }
        for col_idx, width in col_widths.items():
            ws_detail.column_dimensions[get_column_letter(col_idx)].width = width

        # Save workbook to memory buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output
