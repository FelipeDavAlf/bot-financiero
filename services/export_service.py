from collections import defaultdict
from datetime import datetime
import io
import logging
from typing import Dict, List, Tuple
from openpyxl import Workbook
from openpyxl.chart import PieChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from core.database.models import TransactionRecord


# Classification mapping according to standard 50/30/20 personal finance rule
CATEGORY_CLASSIFICATION: Dict[str, Tuple[str, str]] = {
    # Category: (Classification Group, Target Percentage)
    "Alimentación": ("Necesidades Básicas", "50%"),
    "Vivienda y Servicios": ("Necesidades Básicas", "50%"),
    "Transporte": ("Necesidades Básicas", "50%"),
    "Salud y Cuidado": ("Necesidades Básicas", "50%"),
    "Ocio y Entretenimiento": ("Deseos y Estilo de Vida", "30%"),
    "Suscripciones": ("Deseos y Estilo de Vida", "30%"),
    "Mascotas": ("Deseos y Estilo de Vida", "30%"),
    "Otros": ("Deseos y Estilo de Vida", "30%"),
    "Ahorro e Inversión": ("Ahorro e Inversión", "20%"),
}


class ExcelExportService:
    """
    Generates a professional, comprehensive personal finance workbook in Excel.
    Transforms raw transactional data into an actionable financial management template:
    1. 'Resumen Financiero': Executive dashboard, 50/30/20 rule, smart diagnosis, and category breakdown.
    2. 'Presupuesto y Metas': Interactive monthly budget planner with variance and status indicators.
    3. 'Cuentas y Métodos': Liquidity and credit card dependency analysis.
    4. 'Detalle de Movimientos': Complete searchable transaction ledger with formatting and filters.
    """

    def generate_user_finance_workbook(
        self,
        user_name: str,
        transactions: List[TransactionRecord],
    ) -> io.BytesIO:
        """
        Builds and styles the multi-tab financial management workbook.
        Returns an in-memory BytesIO buffer ready to be transmitted via Telegram or downloaded.
        """
        wb = Workbook()

        # Shared style palette
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=16, bold=True, color="0F172A")
        subtitle_font = Font(name="Calibri", size=10, italic=True, color="64748B")
        section_font = Font(name="Calibri", size=12, bold=True, color="0F172A")
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
            bottom=Side(style="double", color="0F172A"),
        )

        # ----------------------------------------------------
        # 1. Sheet 1: Resumen Financiero (Dashboard & Diagnóstico)
        # ----------------------------------------------------
        ws_summary = wb.active
        ws_summary.title = "Resumen Financiero"
        ws_summary.views.sheetView[0].showGridLines = True

        self._build_summary_sheet(
            ws=ws_summary,
            user_name=user_name,
            transactions=transactions,
            styles={
                "header_fill": header_fill,
                "header_font": header_font,
                "title_font": title_font,
                "subtitle_font": subtitle_font,
                "section_font": section_font,
                "bold_font": bold_font,
                "regular_font": regular_font,
                "thin_border": thin_border,
                "total_border": total_border,
            },
        )

        # ----------------------------------------------------
        # 2. Sheet 2: Presupuesto y Metas (Interactive Budget Planner)
        # ----------------------------------------------------
        ws_budget = wb.create_sheet(title="Presupuesto y Metas")
        ws_budget.views.sheetView[0].showGridLines = True
        self._build_budget_sheet(
            ws=ws_budget,
            transactions=transactions,
            styles={
                "header_fill": header_fill,
                "header_font": header_font,
                "title_font": title_font,
                "subtitle_font": subtitle_font,
                "section_font": section_font,
                "bold_font": bold_font,
                "regular_font": regular_font,
                "thin_border": thin_border,
                "total_border": total_border,
            },
        )

        # ----------------------------------------------------
        # 3. Sheet 3: Cuentas y Métodos de Pago (Liquidity & Credit)
        # ----------------------------------------------------
        ws_accounts = wb.create_sheet(title="Cuentas y Métodos")
        ws_accounts.views.sheetView[0].showGridLines = True
        self._build_accounts_sheet(
            ws=ws_accounts,
            transactions=transactions,
            styles={
                "header_fill": header_fill,
                "header_font": header_font,
                "title_font": title_font,
                "subtitle_font": subtitle_font,
                "section_font": section_font,
                "bold_font": bold_font,
                "regular_font": regular_font,
                "thin_border": thin_border,
                "total_border": total_border,
            },
        )

        # ----------------------------------------------------
        # 4. Sheet 4: Detalle de Movimientos (Full Transaction Ledger)
        # ----------------------------------------------------
        ws_detail = wb.create_sheet(title="Detalle de Movimientos")
        ws_detail.views.sheetView[0].showGridLines = True
        self._build_detail_sheet(
            ws=ws_detail,
            transactions=transactions,
            styles={
                "header_fill": header_fill,
                "header_font": header_font,
                "regular_font": regular_font,
                "thin_border": thin_border,
            },
        )

        # Return in-memory buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    def _build_summary_sheet(self, ws, user_name: str, transactions: List[TransactionRecord], styles: dict):
        """Constructs the executive summary dashboard with KPIs, diagnosis, 50/30/20, and monthly trend."""
        # Header Title
        ws["B2"] = "📊 REPORTE DE FINANZAS PERSONALES"
        ws["B2"].font = styles["title_font"]

        emission_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        date_range_str = "Sin movimientos registrados"
        if transactions:
            sorted_dates = sorted(tx.date for tx in transactions)
            date_range_str = f"Período: {sorted_dates[0].strftime('%Y-%m-%d')} al {sorted_dates[-1].strftime('%Y-%m-%d')}"
        ws["B3"] = f"Usuario: {user_name}  |  Fecha de emisión: {emission_date}  |  {date_range_str}"
        ws["B3"].font = styles["subtitle_font"]

        # Financial Calculations
        total_income = sum(float(tx.amount) for tx in transactions if tx.transaction_type == "Ingreso")
        total_expenses = sum(float(tx.amount) for tx in transactions if tx.transaction_type == "Gasto")
        net_balance = total_income - total_expenses
        total_transfers = sum(float(tx.amount) for tx in transactions if tx.transaction_type == "Traspaso")
        savings_rate = (net_balance / total_income) if total_income > 0 else 0.0
        target_savings_20 = total_income * 0.20
        savings_difference = net_balance - target_savings_20

        # Health status badge
        if net_balance < 0:
            health_badge = "🔴 DÉFICIT (<0%)"
            health_color = "991B1B"
            health_bg = "FEE2E2"
        elif savings_rate < 0.10:
            health_badge = "🟠 ALERTA (<10%)"
            health_color = "9A3412"
            health_bg = "FFEDD5"
        elif savings_rate < 0.20:
            health_badge = "🟡 MODERADO (10-19%)"
            health_color = "854D0E"
            health_bg = "FEF9C3"
        else:
            health_badge = "🟢 ÓPTIMO (>=20%)"
            health_color = "166534"
            health_bg = "DCFCE7"

        # KPI Cards (Row 5 & 6) - Preserving B6, C6, D6, E6 for test compatibility
        kpi_configs = [
            ("TOTAL INGRESOS", total_income, "B", "DCFCE7", "166534", "15803D", "$#,##0.00"),
            ("TOTAL GASTOS", total_expenses, "C", "FEE2E2", "991B1B", "B91C1C", "$#,##0.00"),
            ("BALANCE NETO", net_balance, "D", "DBEAFE" if net_balance >= 0 else "FEE2E2", "1E40AF" if net_balance >= 0 else "991B1B", "1D4ED8" if net_balance >= 0 else "B91C1C", "$#,##0.00"),
            ("TRASPASOS", total_transfers, "E", "F1F5F9", "334155", "475569", "$#,##0.00"),
            ("% TASA DE AHORRO", savings_rate, "F", health_bg, health_color, health_color, "0.0%"),
            ("ESTADO FINANCIERO", health_badge, "G", health_bg, health_color, health_color, None),
        ]

        for label, val, col, bg_color, text_color, label_color, num_fmt in kpi_configs:
            lbl_cell = ws[f"{col}5"]
            lbl_cell.value = label
            lbl_cell.font = Font(name="Calibri", size=9, bold=True, color=label_color)
            lbl_cell.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
            lbl_cell.alignment = Alignment(horizontal="center", vertical="center")

            val_cell = ws[f"{col}6"]
            val_cell.value = val
            val_cell.font = Font(name="Calibri", size=13 if col != "G" else 10, bold=True, color=text_color)
            val_cell.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
            val_cell.alignment = Alignment(horizontal="center", vertical="center")
            if num_fmt:
                val_cell.number_format = num_fmt

        ws.row_dimensions[5].height = 20
        ws.row_dimensions[6].height = 28

        # ----------------------------------------------------
        # 1.1 Diagnóstico Financiero y Plan de Acción (Rows 8-12)
        # ----------------------------------------------------
        ws["B8"] = "💡 DIAGNÓSTICO FINANCIERO Y PLAN DE ACCIÓN"
        ws["B8"].font = styles["section_font"]

        # Category aggregation for diagnosis
        category_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {"amount": 0.0, "count": 0})
        for tx in transactions:
            if tx.transaction_type == "Gasto":
                cat = tx.category or "Otros"
                category_stats[cat]["amount"] += float(tx.amount)
                category_stats[cat]["count"] += 1

        sorted_categories = sorted(category_stats.items(), key=lambda x: x[1]["amount"], reverse=True)
        top_cat_name = sorted_categories[0][0] if sorted_categories else "Sin gastos"
        top_cat_amt = sorted_categories[0][1]["amount"] if sorted_categories else 0.0
        top_cat_pct = (top_cat_amt / total_expenses) if total_expenses > 0 else 0.0

        # Formulate actionable diagnostic advice
        if net_balance < 0:
            advice_action = f"⚠️ Estás operando en déficit de -${abs(net_balance):,.2f}. Prioriza congelar compras en {top_cat_name} y auditar suscripciones."
        elif savings_rate < 0.20:
            advice_action = f"🎯 Para alcanzar la meta óptima del 20% (${target_savings_20:,.2f}), necesitas ahorrar ${abs(savings_difference):,.2f} más, reduciendo gastos en {top_cat_name}."
        else:
            advice_action = f"🎉 ¡Excelente salud financiera! Mantienes un ahorro de {savings_rate*100:.1f}%. Considera invertir tu excedente de ${net_balance:,.2f} en CETES o fondos de ahorro."

        diag_lines = [
            f"• 💰 Tasa de Ahorro: {savings_rate * 100:.1f}% de tus ingresos (Meta estándar recomendada: 20.0%).",
            f"• 🚨 Mayor salida de dinero: '{top_cat_name}' absorbe ${top_cat_amt:,.2f} ({top_cat_pct * 100:.1f}% de tus gastos totales).",
            f"• 📌 Recomendación: {advice_action}",
        ]

        diag_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        for idx, line in enumerate(diag_lines, start=9):
            ws.merge_cells(f"B{idx}:G{idx}")
            diag_cell = ws[f"B{idx}"]
            diag_cell.value = line
            diag_cell.font = Font(name="Calibri", size=10, color="1E293B", bold=(idx == 11))
            diag_cell.fill = diag_fill
            diag_cell.alignment = Alignment(horizontal="left", vertical="center")
            ws.row_dimensions[idx].height = 20

        # ----------------------------------------------------
        # 1.2 Regla 50 / 30 / 20 (Necesidades vs Deseos vs Ahorro)
        # ----------------------------------------------------
        ws["B14"] = "⚖️ ANÁLISIS DE DISTRIBUCIÓN REGLA 50 / 30 / 20"
        ws["B14"].font = styles["section_font"]

        rule_headers = ["Pilar Financiero", "Monto Real", "% Real", "% Recomendado", "Diferencia", "Diagnóstico"]
        for col_idx, h_text in enumerate(rule_headers, start=2):
            c = ws.cell(row=15, column=col_idx, value=h_text)
            c.fill = styles["header_fill"]
            c.font = styles["header_font"]
            c.alignment = Alignment(horizontal="center" if col_idx > 2 else "left", vertical="center")
        ws.row_dimensions[15].height = 24

        needs_amt = sum(stats["amount"] for cat, stats in category_stats.items() if CATEGORY_CLASSIFICATION.get(cat, ("Deseos", ""))[0] == "Necesidades Básicas")
        wants_amt = sum(stats["amount"] for cat, stats in category_stats.items() if CATEGORY_CLASSIFICATION.get(cat, ("Deseos", ""))[0] == "Deseos y Estilo de Vida")
        savings_invest_amt = max(net_balance, 0.0) + sum(stats["amount"] for cat, stats in category_stats.items() if cat == "Ahorro e Inversión")

        needs_pct = (needs_amt / total_income) if total_income > 0 else 0.0
        wants_pct = (wants_amt / total_income) if total_income > 0 else 0.0
        savings_pct = (savings_invest_amt / total_income) if total_income > 0 else 0.0

        rule_rows = [
            ("Necesidades Básicas (Vivienda, Super, Salud, Transporte)", needs_amt, needs_pct, 0.50, "Bajo control (<=50%)" if needs_pct <= 0.50 else "Elevado (>50%)"),
            ("Deseos y Estilo de Vida (Ocio, Restaurantes, Suscripciones)", wants_amt, wants_pct, 0.30, "Moderado (<=30%)" if wants_pct <= 0.30 else "Excesivo (>30%)"),
            ("Ahorro e Inversión (Ahorro Neto + Inversiones)", savings_invest_amt, savings_pct, 0.20, "Meta Cumplida (>=20%)" if savings_pct >= 0.20 else "Insuficiente (<20%)"),
        ]

        curr_r = 16
        for name, amt, pct, rec_pct, diag in rule_rows:
            ws[f"B{curr_r}"].value = name
            ws[f"B{curr_r}"].font = styles["regular_font"]
            ws[f"B{curr_r}"].border = styles["thin_border"]

            ws[f"C{curr_r}"].value = amt
            ws[f"C{curr_r}"].font = styles["regular_font"]
            ws[f"C{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"C{curr_r}"].number_format = "$#,##0.00"
            ws[f"C{curr_r}"].border = styles["thin_border"]

            ws[f"D{curr_r}"].value = pct
            ws[f"D{curr_r}"].font = styles["bold_font"]
            ws[f"D{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"D{curr_r}"].number_format = "0.0%"
            ws[f"D{curr_r}"].border = styles["thin_border"]

            ws[f"E{curr_r}"].value = rec_pct
            ws[f"E{curr_r}"].font = styles["regular_font"]
            ws[f"E{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"E{curr_r}"].number_format = "0.0%"
            ws[f"E{curr_r}"].border = styles["thin_border"]

            diff_val = pct - rec_pct
            ws[f"F{curr_r}"].value = diff_val
            ws[f"F{curr_r}"].font = styles["regular_font"]
            ws[f"F{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"F{curr_r}"].number_format = "+0.0%;-0.0%;0.0%"
            ws[f"F{curr_r}"].border = styles["thin_border"]

            ws[f"G{curr_r}"].value = diag
            ws[f"G{curr_r}"].font = Font(name="Calibri", size=10, bold=True, color="166534" if ("Cumplida" in diag or "control" in diag or "Moderado" in diag) else "991B1B")
            ws[f"G{curr_r}"].alignment = Alignment(horizontal="center", vertical="center")
            ws[f"G{curr_r}"].border = styles["thin_border"]
            ws.row_dimensions[curr_r].height = 20
            curr_r += 1

        # ----------------------------------------------------
        # 1.3 Desglose de Gastos por Categoría (Row 21)
        # ----------------------------------------------------
        curr_r = 21
        ws[f"B{curr_r}"] = "🏷️ DESGLOSE DE GASTOS POR CATEGORÍA"
        ws[f"B{curr_r}"].font = styles["section_font"]

        cat_headers = ["Categoría", "Monto Gastado", "% del Total", "Transacciones"]
        header_r = curr_r + 1
        for idx, header in enumerate(cat_headers, start=2):
            col_letter = get_column_letter(idx)
            cell = ws[f"{col_letter}{header_r}"]
            cell.value = header
            cell.fill = styles["header_fill"]
            cell.font = styles["header_font"]
            cell.alignment = Alignment(horizontal="center" if idx > 2 else "left", vertical="center")
        ws.row_dimensions[header_r].height = 24

        cat_start_row = header_r + 1
        cat_r = cat_start_row
        for cat_name, stats in sorted_categories:
            amount = stats["amount"]
            count = stats["count"]
            pct = (amount / total_expenses) if total_expenses > 0 else 0.0

            row_fill = PatternFill(start_color="F8FAFC" if cat_r % 2 == 0 else "FFFFFF", fill_type="solid")

            # Col B: Categoría
            ws[f"B{cat_r}"].value = cat_name
            ws[f"B{cat_r}"].font = styles["regular_font"]
            ws[f"B{cat_r}"].fill = row_fill
            ws[f"B{cat_r}"].border = styles["thin_border"]

            # Col C: Monto
            ws[f"C{cat_r}"].value = amount
            ws[f"C{cat_r}"].font = styles["regular_font"]
            ws[f"C{cat_r}"].fill = row_fill
            ws[f"C{cat_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"C{cat_r}"].number_format = "$#,##0.00"
            ws[f"C{cat_r}"].border = styles["thin_border"]

            # Col D: % del Total
            ws[f"D{cat_r}"].value = pct
            ws[f"D{cat_r}"].font = styles["regular_font"]
            ws[f"D{cat_r}"].fill = row_fill
            ws[f"D{cat_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"D{cat_r}"].number_format = "0.0%"
            ws[f"D{cat_r}"].border = styles["thin_border"]

            # Col E: Transacciones
            ws[f"E{cat_r}"].value = count
            ws[f"E{cat_r}"].font = styles["regular_font"]
            ws[f"E{cat_r}"].fill = row_fill
            ws[f"E{cat_r}"].alignment = Alignment(horizontal="center", vertical="center")
            ws[f"E{cat_r}"].border = styles["thin_border"]

            ws.row_dimensions[cat_r].height = 20
            cat_r += 1

        cat_end_row = max(cat_r - 1, cat_start_row)

        # Total Row for Category Table
        ws[f"B{cat_r}"].value = "TOTAL GASTOS"
        ws[f"B{cat_r}"].font = styles["bold_font"]
        ws[f"B{cat_r}"].border = styles["total_border"]

        ws[f"C{cat_r}"].value = total_expenses
        ws[f"C{cat_r}"].font = styles["bold_font"]
        ws[f"C{cat_r}"].alignment = Alignment(horizontal="right", vertical="center")
        ws[f"C{cat_r}"].number_format = "$#,##0.00"
        ws[f"C{cat_r}"].border = styles["total_border"]

        ws[f"D{cat_r}"].value = 1.0 if total_expenses > 0 else 0.0
        ws[f"D{cat_r}"].font = styles["bold_font"]
        ws[f"D{cat_r}"].alignment = Alignment(horizontal="right", vertical="center")
        ws[f"D{cat_r}"].number_format = "0.0%"
        ws[f"D{cat_r}"].border = styles["total_border"]

        ws[f"E{cat_r}"].value = sum(s["count"] for s in category_stats.values())
        ws[f"E{cat_r}"].font = styles["bold_font"]
        ws[f"E{cat_r}"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"E{cat_r}"].border = styles["total_border"]
        ws.row_dimensions[cat_r].height = 22

        # Embed Category Pie Chart if there are expenses
        if sorted_categories and total_expenses > 0:
            try:
                pie = PieChart()
                pie.title = "Distribución de Gastos por Categoría"
                pie.width = 15
                pie.height = 9
                data = Reference(ws, min_col=3, min_row=cat_start_row - 1, max_row=cat_end_row)
                labels = Reference(ws, min_col=2, min_row=cat_start_row, max_row=cat_end_row)
                pie.add_data(data, titles_from_data=True)
                pie.set_categories(labels)
                ws.add_chart(pie, "F21")
            except Exception as exc:
                logging.debug(f"Could not embed pie chart: {exc}")

        # ----------------------------------------------------
        # 1.4 Evolución Mensual (Tendencia Histórica)
        # ----------------------------------------------------
        trend_r = cat_r + 3
        ws[f"B{trend_r}"] = "📅 EVOLUCIÓN HISTÓRICA POR MES"
        ws[f"B{trend_r}"].font = styles["section_font"]

        trend_headers = ["Mes", "Ingresos", "Gastos", "Balance Neto", "% Ahorro", "Meta 20%"]
        trend_hr = trend_r + 1
        for idx, h_text in enumerate(trend_headers, start=2):
            c = ws.cell(row=trend_hr, column=idx, value=h_text)
            c.fill = styles["header_fill"]
            c.font = styles["header_font"]
            c.alignment = Alignment(horizontal="center" if idx > 2 else "left", vertical="center")
        ws.row_dimensions[trend_hr].height = 24

        # Group by Year-Month
        monthly_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
        for tx in transactions:
            ym = tx.date.strftime("%Y-%m")
            if tx.transaction_type == "Ingreso":
                monthly_stats[ym]["income"] += float(tx.amount)
            elif tx.transaction_type == "Gasto":
                monthly_stats[ym]["expense"] += float(tx.amount)

        sorted_months = sorted(monthly_stats.items(), key=lambda x: x[0])
        m_r = trend_hr + 1
        for ym, m_data in sorted_months:
            m_inc = m_data["income"]
            m_exp = m_data["expense"]
            m_bal = m_inc - m_exp
            m_rate = (m_bal / m_inc) if m_inc > 0 else 0.0
            m_hit = "✅ Cumplida" if m_rate >= 0.20 else "⚠️ No alcanzada"

            ws[f"B{m_r}"].value = ym
            ws[f"B{m_r}"].font = styles["regular_font"]
            ws[f"B{m_r}"].border = styles["thin_border"]

            ws[f"C{m_r}"].value = m_inc
            ws[f"C{m_r}"].font = styles["regular_font"]
            ws[f"C{m_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"C{m_r}"].number_format = "$#,##0.00"
            ws[f"C{m_r}"].border = styles["thin_border"]

            ws[f"D{m_r}"].value = m_exp
            ws[f"D{m_r}"].font = styles["regular_font"]
            ws[f"D{m_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"D{m_r}"].number_format = "$#,##0.00"
            ws[f"D{m_r}"].border = styles["thin_border"]

            ws[f"E{m_r}"].value = m_bal
            ws[f"E{m_r}"].font = styles["bold_font"]
            ws[f"E{m_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"E{m_r}"].number_format = "$#,##0.00"
            ws[f"E{m_r}"].border = styles["thin_border"]

            ws[f"F{m_r}"].value = m_rate
            ws[f"F{m_r}"].font = styles["bold_font"]
            ws[f"F{m_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"F{m_r}"].number_format = "0.0%"
            ws[f"F{m_r}"].border = styles["thin_border"]

            ws[f"G{m_r}"].value = m_hit
            ws[f"G{m_r}"].font = Font(name="Calibri", size=10, bold=True, color="166534" if "Cumplida" in m_hit else "991B1B")
            ws[f"G{m_r}"].alignment = Alignment(horizontal="center", vertical="center")
            ws[f"G{m_r}"].border = styles["thin_border"]
            ws.row_dimensions[m_r].height = 20
            m_r += 1

        # Adjust column widths for Summary sheet
        ws.column_dimensions["A"].width = 3
        ws.column_dimensions["B"].width = 36
        ws.column_dimensions["C"].width = 20
        ws.column_dimensions["D"].width = 20
        ws.column_dimensions["E"].width = 18
        ws.column_dimensions["F"].width = 22
        ws.column_dimensions["G"].width = 28

    def _build_budget_sheet(self, ws, transactions: List[TransactionRecord], styles: dict):
        """Constructs an interactive monthly budget planner where users can adjust budget allocations and track variance."""
        ws["B2"] = "🎯 PLANIFICADOR MENSUAL DE PRESUPUESTO Y METAS"
        ws["B2"].font = styles["title_font"]

        ws["B3"] = "💡 Puedes editar la columna 'Presupuesto Asignado' con tus metas mensuales. Las fórmulas calcularán tu saldo disponible y nivel de alerta."
        ws["B3"].font = styles["subtitle_font"]

        headers = [
            "Categoría",
            "Pilar 50/30/20",
            "Presupuesto Asignado (Meta)",
            "Gasto Real Actual",
            "Saldo Disponible",
            "% Consumido",
            "Semáforo",
        ]

        header_row = 5
        for col_idx, h_text in enumerate(headers, start=2):
            cell = ws.cell(row=header_row, column=col_idx, value=h_text)
            cell.fill = styles["header_fill"]
            cell.font = styles["header_font"]
            cell.alignment = Alignment(horizontal="center" if col_idx > 3 else "left", vertical="center")
        ws.row_dimensions[header_row].height = 26

        # Calculate actual expenses per category
        actual_expenses: Dict[str, float] = defaultdict(float)
        for tx in transactions:
            if tx.transaction_type == "Gasto":
                cat = tx.category or "Otros"
                actual_expenses[cat] += float(tx.amount)

        # Standard list of categories
        standard_categories = [
            "Alimentación",
            "Vivienda y Servicios",
            "Transporte",
            "Salud y Cuidado",
            "Ocio y Entretenimiento",
            "Suscripciones",
            "Mascotas",
            "Ahorro e Inversión",
            "Otros",
        ]
        # Include any extra categories the user might have logged
        for cat in actual_expenses:
            if cat not in standard_categories:
                standard_categories.append(cat)

        curr_r = 6
        for cat in standard_categories:
            classification, _ = CATEGORY_CLASSIFICATION.get(cat, ("Deseos y Estilo de Vida", "30%"))
            actual_amt = actual_expenses.get(cat, 0.0)
            # Default suggested budget: actual amount rounded up or reasonable base
            suggested_budget = max(round(actual_amt * 1.1, -1), 500.0) if actual_amt > 0 else 1000.0

            # Col B: Categoría
            ws[f"B{curr_r}"].value = cat
            ws[f"B{curr_r}"].font = styles["bold_font"]
            ws[f"B{curr_r}"].border = styles["thin_border"]

            # Col C: Pilar
            ws[f"C{curr_r}"].value = classification
            ws[f"C{curr_r}"].font = styles["regular_font"]
            ws[f"C{curr_r}"].border = styles["thin_border"]

            # Col D: Presupuesto Asignado (Editable by user)
            ws[f"D{curr_r}"].value = suggested_budget
            ws[f"D{curr_r}"].font = Font(name="Calibri", size=11, bold=True, color="1E40AF")
            ws[f"D{curr_r}"].fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
            ws[f"D{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"D{curr_r}"].number_format = "$#,##0.00"
            ws[f"D{curr_r}"].border = styles["thin_border"]

            # Col E: Gasto Real Actual
            ws[f"E{curr_r}"].value = actual_amt
            ws[f"E{curr_r}"].font = styles["regular_font"]
            ws[f"E{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"E{curr_r}"].number_format = "$#,##0.00"
            ws[f"E{curr_r}"].border = styles["thin_border"]

            # Col F: Saldo Disponible (Excel Formula: =Presupuesto - Real)
            ws[f"F{curr_r}"].value = f"=D{curr_r}-E{curr_r}"
            ws[f"F{curr_r}"].font = styles["bold_font"]
            ws[f"F{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"F{curr_r}"].number_format = "$#,##0.00"
            ws[f"F{curr_r}"].border = styles["thin_border"]

            # Col G: % Consumido (Excel Formula: =IF(D>0, E/D, 0))
            ws[f"G{curr_r}"].value = f"=IF(D{curr_r}>0, E{curr_r}/D{curr_r}, 0)"
            ws[f"G{curr_r}"].font = styles["bold_font"]
            ws[f"G{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"G{curr_r}"].number_format = "0.0%"
            ws[f"G{curr_r}"].border = styles["thin_border"]

            # Col H: Semáforo (Excel Formula)
            ws[f"H{curr_r}"].value = f'=IF(F{curr_r}<0, "🔴 EXCEDIDO", IF(G{curr_r}>=0.85, "🟡 ALERTA", "🟢 EN CONTROL"))'
            ws[f"H{curr_r}"].font = styles["bold_font"]
            ws[f"H{curr_r}"].alignment = Alignment(horizontal="center", vertical="center")
            ws[f"H{curr_r}"].border = styles["thin_border"]

            ws.row_dimensions[curr_r].height = 20
            curr_r += 1

        last_cat_row = curr_r - 1

        # Total Row
        ws[f"B{curr_r}"].value = "TOTAL PRESUPUESTO"
        ws[f"B{curr_r}"].font = styles["bold_font"]
        ws[f"B{curr_r}"].border = styles["total_border"]

        ws[f"C{curr_r}"].value = "-"
        ws[f"C{curr_r}"].font = styles["bold_font"]
        ws[f"C{curr_r}"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"C{curr_r}"].border = styles["total_border"]

        ws[f"D{curr_r}"].value = f"=SUM(D6:D{last_cat_row})"
        ws[f"D{curr_r}"].font = styles["bold_font"]
        ws[f"D{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
        ws[f"D{curr_r}"].number_format = "$#,##0.00"
        ws[f"D{curr_r}"].border = styles["total_border"]

        ws[f"E{curr_r}"].value = f"=SUM(E6:E{last_cat_row})"
        ws[f"E{curr_r}"].font = styles["bold_font"]
        ws[f"E{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
        ws[f"E{curr_r}"].number_format = "$#,##0.00"
        ws[f"E{curr_r}"].border = styles["total_border"]

        ws[f"F{curr_r}"].value = f"=D{curr_r}-E{curr_r}"
        ws[f"F{curr_r}"].font = styles["bold_font"]
        ws[f"F{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
        ws[f"F{curr_r}"].number_format = "$#,##0.00"
        ws[f"F{curr_r}"].border = styles["total_border"]

        ws[f"G{curr_r}"].value = f"=IF(D{curr_r}>0, E{curr_r}/D{curr_r}, 0)"
        ws[f"G{curr_r}"].font = styles["bold_font"]
        ws[f"G{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
        ws[f"G{curr_r}"].number_format = "0.0%"
        ws[f"G{curr_r}"].border = styles["total_border"]

        ws[f"H{curr_r}"].value = f'=IF(F{curr_r}<0, "🔴 EXCEDIDO", "🟢 EN CONTROL")'
        ws[f"H{curr_r}"].font = styles["bold_font"]
        ws[f"H{curr_r}"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"H{curr_r}"].border = styles["total_border"]
        ws.row_dimensions[curr_r].height = 22

        # Column widths
        ws.column_dimensions["A"].width = 3
        ws.column_dimensions["B"].width = 28
        ws.column_dimensions["C"].width = 24
        ws.column_dimensions["D"].width = 26
        ws.column_dimensions["E"].width = 22
        ws.column_dimensions["F"].width = 22
        ws.column_dimensions["G"].width = 18
        ws.column_dimensions["H"].width = 20

    def _build_accounts_sheet(self, ws, transactions: List[TransactionRecord], styles: dict):
        """Constructs payment method and account breakdown to analyze credit dependency and cash flow."""
        ws["B2"] = "💳 ANÁLISIS DE CUENTAS Y FORMAS DE PAGO"
        ws["B2"].font = styles["title_font"]

        ws["B3"] = "Monitorea cuánto gastas en Tarjetas de Crédito vs Débito y Efectivo para prevenir endeudamiento."
        ws["B3"].font = styles["subtitle_font"]

        headers = ["Cuenta / Tarjeta", "Tipo de Cuenta", "Total Egresos", "% del Gasto", "Total Ingresos", "Movimientos"]
        for col_idx, h_text in enumerate(headers, start=2):
            c = ws.cell(row=5, column=col_idx, value=h_text)
            c.fill = styles["header_fill"]
            c.font = styles["header_font"]
            c.alignment = Alignment(horizontal="center" if col_idx > 2 else "left", vertical="center")
        ws.row_dimensions[5].height = 26

        account_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {"expense": 0.0, "income": 0.0, "count": 0})
        total_expense = sum(float(tx.amount) for tx in transactions if tx.transaction_type == "Gasto")

        for tx in transactions:
            acc = tx.source_account_name or "Sin especificar"
            if tx.transaction_type == "Gasto":
                account_stats[acc]["expense"] += float(tx.amount)
                account_stats[acc]["count"] += 1
            elif tx.transaction_type == "Ingreso":
                account_stats[acc]["income"] += float(tx.amount)
                account_stats[acc]["count"] += 1

        credit_expense = 0.0
        debit_cash_expense = 0.0

        curr_r = 6
        for acc_name, stats in sorted(account_stats.items(), key=lambda x: x[1]["expense"], reverse=True):
            exp = stats["expense"]
            inc = stats["income"]
            cnt = int(stats["count"])
            pct = (exp / total_expense) if total_expense > 0 else 0.0

            # Infer type for metrics
            lower_name = acc_name.lower()
            if any(k in lower_name for k in ["crédito", "credito", "rappi"]):
                acc_type = "Crédito"
                credit_expense += exp
            elif any(k in lower_name for k in ["débito", "debito", "cheques", "nómina", "nomina"]):
                acc_type = "Débito"
                debit_cash_expense += exp
            elif any(k in lower_name for k in ["efectivo", "cash"]):
                acc_type = "Efectivo"
                debit_cash_expense += exp
            else:
                acc_type = "General"
                debit_cash_expense += exp

            row_fill = PatternFill(start_color="F8FAFC" if curr_r % 2 == 0 else "FFFFFF", fill_type="solid")

            ws[f"B{curr_r}"].value = acc_name
            ws[f"B{curr_r}"].font = styles["regular_font"]
            ws[f"B{curr_r}"].fill = row_fill
            ws[f"B{curr_r}"].border = styles["thin_border"]

            ws[f"C{curr_r}"].value = acc_type
            ws[f"C{curr_r}"].font = Font(name="Calibri", size=11, bold=True, color="991B1B" if acc_type == "Crédito" else "1E40AF")
            ws[f"C{curr_r}"].fill = row_fill
            ws[f"C{curr_r}"].alignment = Alignment(horizontal="center", vertical="center")
            ws[f"C{curr_r}"].border = styles["thin_border"]

            ws[f"D{curr_r}"].value = exp
            ws[f"D{curr_r}"].font = styles["regular_font"]
            ws[f"D{curr_r}"].fill = row_fill
            ws[f"D{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"D{curr_r}"].number_format = "$#,##0.00"
            ws[f"D{curr_r}"].border = styles["thin_border"]

            ws[f"E{curr_r}"].value = pct
            ws[f"E{curr_r}"].font = styles["regular_font"]
            ws[f"E{curr_r}"].fill = row_fill
            ws[f"E{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"E{curr_r}"].number_format = "0.0%"
            ws[f"E{curr_r}"].border = styles["thin_border"]

            ws[f"F{curr_r}"].value = inc
            ws[f"F{curr_r}"].font = styles["regular_font"]
            ws[f"F{curr_r}"].fill = row_fill
            ws[f"F{curr_r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"F{curr_r}"].number_format = "$#,##0.00"
            ws[f"F{curr_r}"].border = styles["thin_border"]

            ws[f"G{curr_r}"].value = cnt
            ws[f"G{curr_r}"].font = styles["regular_font"]
            ws[f"G{curr_r}"].fill = row_fill
            ws[f"G{curr_r}"].alignment = Alignment(horizontal="center", vertical="center")
            ws[f"G{curr_r}"].border = styles["thin_border"]

            ws.row_dimensions[curr_r].height = 20
            curr_r += 1

        # Summary box: Credit Dependency
        summary_r = curr_r + 2
        ws[f"B{summary_r}"] = "📊 INDICADOR DE ENDEUDAMIENTO Y CRÉDITO"
        ws[f"B{summary_r}"].font = styles["section_font"]

        credit_ratio = (credit_expense / total_expense) if total_expense > 0 else 0.0
        if credit_ratio > 0.60:
            credit_diag = "⚠️ RIESGO ALTO: Más del 60% de tus gastos se cargan a crédito. Monitorea tu capacidad de pago total a fin de mes."
            credit_color = "991B1B"
        else:
            credit_diag = "✅ USO SALUDABLE: Tu uso de tarjetas de crédito se mantiene en niveles manejables frente a tus ingresos."
            credit_color = "166534"

        ws[f"B{summary_r + 1}"] = f"• Gasto en Tarjetas de Crédito: ${credit_expense:,.2f} ({credit_ratio * 100:.1f}% de tus gastos totales)."
        ws[f"B{summary_r + 1}"].font = styles["regular_font"]

        ws[f"B{summary_r + 2}"] = f"• Gasto en Débito / Efectivo: ${debit_cash_expense:,.2f} ({(1.0 - credit_ratio) * 100:.1f}% de tus gastos totales)."
        ws[f"B{summary_r + 2}"].font = styles["regular_font"]

        ws[f"B{summary_r + 3}"] = f"• Diagnóstico de Crédito: {credit_diag}"
        ws[f"B{summary_r + 3}"].font = Font(name="Calibri", size=11, bold=True, color=credit_color)

        ws.column_dimensions["A"].width = 3
        ws.column_dimensions["B"].width = 30
        ws.column_dimensions["C"].width = 18
        ws.column_dimensions["D"].width = 20
        ws.column_dimensions["E"].width = 18
        ws.column_dimensions["F"].width = 20
        ws.column_dimensions["G"].width = 16

    def _build_detail_sheet(self, ws, transactions: List[TransactionRecord], styles: dict):
        """Constructs the comprehensive, filterable detailed transaction ledger."""
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
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.fill = styles["header_fill"]
            cell.font = styles["header_font"]
            cell.alignment = Alignment(horizontal="center", vertical="center")

        ws.row_dimensions[1].height = 26

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
            c1 = ws.cell(row=row_idx, column=1, value=row_idx - 1)
            c1.alignment = Alignment(horizontal="center", vertical="center")
            c1.font = styles["regular_font"]
            c1.fill = base_fill
            c1.border = styles["thin_border"]

            # Col 2: Fecha
            c2 = ws.cell(row=row_idx, column=2, value=tx.date.strftime("%Y-%m-%d"))
            c2.alignment = Alignment(horizontal="center", vertical="center")
            c2.font = styles["regular_font"]
            c2.fill = base_fill
            c2.border = styles["thin_border"]

            # Col 3: Tipo
            c3 = ws.cell(row=row_idx, column=3, value=tx.transaction_type)
            c3.alignment = Alignment(horizontal="center", vertical="center")
            type_cfg = type_styles.get(tx.transaction_type, {"font_color": "0F172A", "bg_color": base_bg})
            c3.font = Font(name="Calibri", size=11, bold=True, color=type_cfg["font_color"])
            c3.fill = PatternFill(start_color=type_cfg["bg_color"], end_color=type_cfg["bg_color"], fill_type="solid")
            c3.border = styles["thin_border"]

            # Col 4: Monto
            c4 = ws.cell(row=row_idx, column=4, value=float(tx.amount))
            c4.alignment = Alignment(horizontal="right", vertical="center")
            c4.font = Font(name="Calibri", size=11, bold=True, color="0F172A")
            c4.number_format = "$#,##0.00"
            c4.fill = base_fill
            c4.border = styles["thin_border"]

            # Col 5: Categoría
            c5 = ws.cell(row=row_idx, column=5, value=tx.category or "")
            c5.font = styles["regular_font"]
            c5.fill = base_fill
            c5.border = styles["thin_border"]

            # Col 6: Subcategoría
            c6 = ws.cell(row=row_idx, column=6, value=tx.subcategory or "")
            c6.font = styles["regular_font"]
            c6.fill = base_fill
            c6.border = styles["thin_border"]

            # Col 7: Cuenta Origen
            c7 = ws.cell(row=row_idx, column=7, value=tx.source_account_name or "N/A")
            c7.font = styles["regular_font"]
            c7.fill = base_fill
            c7.border = styles["thin_border"]

            # Col 8: Cuenta Destino
            c8 = ws.cell(row=row_idx, column=8, value=tx.destination_account_name or "N/A")
            c8.font = styles["regular_font"]
            c8.fill = base_fill
            c8.border = styles["thin_border"]

            # Col 9: Descripción
            c9 = ws.cell(row=row_idx, column=9, value=tx.description or "")
            c9.font = styles["regular_font"]
            c9.fill = base_fill
            c9.border = styles["thin_border"]

            ws.row_dimensions[row_idx].height = 20

        # Enable auto-filters and freeze panes
        last_row = max(len(transactions) + 1, 2)
        ws.auto_filter.ref = f"A1:I{last_row}"
        ws.freeze_panes = "A2"

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
            ws.column_dimensions[get_column_letter(col_idx)].width = width
