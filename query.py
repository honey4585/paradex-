#!/usr/bin/env python3
"""
Paradex PnL Reader - Season 2 Ultimate Edition (v5.2)
修复日志：
1. [核心修复] 地址查询逻辑优化为单次调用。解决了因短时间两次请求导致 Excel 中地址为空的问题。
2. [配置清理] 再次重置 GROUPS，确保 Group 3 中不包含 5.x 账户，消除重复显示。
3. [功能] 保持 Excel 自动导出功能。
"""

import os
import sys
import json
import threading
import time
from datetime import datetime, timedelta, timezone

# 1. 依赖库检查与导入
try:
    import requests
    from dotenv import load_dotenv
    import tkinter as tk
    from tkinter import scrolledtext, ttk, messagebox
    import pandas as pd
except ImportError as e:
    print(f"❌ 启动失败：缺少必要库 -> {e}")
    print("请运行: pip install requests python-dotenv pandas openpyxl")
    sys.exit(1)

# ================= 配置与环境加载 =================
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'para.env')
load_dotenv(env_path)

API_BASE_URL = "https://api.prod.paradex.trade/v1"
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs/stats_cache.json")
EXCEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")

# 账户组配置 (请全选覆盖，不要保留旧配置)
GROUPS = [
    {
        "id": 0, "name": "Group 0 ",
        "accounts": [
            {"name": "Acc 0.1", "key": os.getenv("PARADEX_API_KEY_0_1")},
            {"name": "Acc 0.2", "key": os.getenv("PARADEX_API_KEY_0_2")}
        ]
    },
    {
        "id": 1, "name": "Group 1 ",
        "accounts": [
            {"name": "Acc 1.1", "key": os.getenv("PARADEX_API_KEY_1_1")},
            {"name": "Acc 1.2", "key": os.getenv("PARADEX_API_KEY_1_2")}
        ]
    },
    {
        "id": 2, "name": "Group 2 ",
        "accounts": [
            {"name": "Acc 2.1", "key": os.getenv("PARADEX_API_KEY_2_1")},
            {"name": "Acc 2.2", "key": os.getenv("PARADEX_API_KEY_2_2")}
        ]
    },
    {
        "id": 3, "name": "Group 3 ",
        "accounts": [
            # 确保这里只有 3.x，不要有 5.x
            {"name": "Acc 3.1", "key": os.getenv("PARADEX_API_KEY_3_1")},
            {"name": "Acc 3.2", "key": os.getenv("PARADEX_API_KEY_3_2")}
        ]
    },
    {
        "id": 4, "name": "Group 4 ",
        "accounts": [
            {"name": "Acc 4.1", "key": os.getenv("PARADEX_API_KEY_4_1")},
            {"name": "Acc 4.2", "key": os.getenv("PARADEX_API_KEY_4_2")}
        ]
    },
    {
        "id": 5, "name": "Group 5 ",
        "accounts": [
            {"name": "Acc 5.1", "key": os.getenv("PARADEX_API_KEY_5_1")},
            {"name": "Acc 5.2", "key": os.getenv("PARADEX_API_KEY_5_2")}
        ]
    },
    {
        "id": 6, "name": "Group 6 ",
        "accounts": [
            {"name": "Acc 6.1", "key": os.getenv("PARADEX_API_KEY_6_1")},
            {"name": "Acc 6.2", "key": os.getenv("PARADEX_API_KEY_6_2")}
        ]
    }
]

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# ⚠️ 代理配置
PROXY_CONFIG = {
    'http': 'http://127.0.0.1:10808',
    'https': 'http://127.0.0.1:10808'
}
# PROXY_CONFIG = None 

# ================= 缓存管理 =================
def load_json(filepath):
    if not os.path.exists(filepath): return {}
    try:
        with open(filepath, 'r') as f: return json.load(f)
    except: return {}

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, 'w') as f: json.dump(data, f, indent=2)
    except Exception as e: print(f"Save failed: {e}")

STATS_CACHE = load_json(CACHE_FILE)

# ================= 核心 API 功能 =================

def fetch_address_unified(api_key):
    """
    [核心修复] 统一获取账户地址
    只调用一次 API，同时供 UI 和 Excel 使用，避免限流。
    """
    if not api_key: return ""
    try:
        endpoint = f"{API_BASE_URL}/account/info"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            resp = requests.get(endpoint, headers=headers, timeout=10)
        except:
            if PROXY_CONFIG: resp = requests.get(endpoint, headers=headers, proxies=PROXY_CONFIG, timeout=10)
            else: raise
        
        if resp.status_code == 200:
            data = resp.json()
            if "results" in data and len(data["results"]) > 0:
                return data["results"][0].get("account", "")
    except:
        return ""
    return ""

def fetch_xp_combined(api_key):
    """
    获取 Season 2 XP 详情
    """
    if not api_key: return 0.0, 0.0, 0, 0.0, 0.0
    
    total_xp = 0.0
    earned_xp = 0.0
    transferable_xp = 0.0
    latest_week_xp = 0.0
    latest_week_num = 0
    
    headers = {"Authorization": f"Bearer {api_key}"}

    # 1. 获取账户 XP 余额
    try:
        url_balance = f"{API_BASE_URL}/xp/account-balance?season=season2"
        try:
            resp = requests.get(url_balance, headers=headers, timeout=10)
        except:
            if PROXY_CONFIG: resp = requests.get(url_balance, headers=headers, proxies=PROXY_CONFIG, timeout=10)
            else: raise
        
        if resp.status_code == 200:
            data = resp.json()
            earned_xp = float(data.get("earned_xp", 0))
            transferable_xp = float(data.get("transferrable_xp", 0))
            total_xp = earned_xp
    except: pass

    # 2. 获取历史周分
    try:
        url_history = f"{API_BASE_URL}/campaigns/private/points/history/season2"
        try:
            resp = requests.get(url_history, headers=headers, timeout=10)
        except:
            if PROXY_CONFIG: resp = requests.get(url_history, headers=headers, proxies=PROXY_CONFIG, timeout=10)
            else: raise
            
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                results.sort(key=lambda x: int(x.get("week", 0)))
                latest = results[-1]
                latest_week_num = int(latest.get("week", 0))
                latest_week_xp = float(latest.get("points", {}).get("total", 0))
    except: pass
    
    return total_xp, latest_week_xp, latest_week_num, earned_xp, transferable_xp

def fetch_transfers_incremental(api_key, cache_key, log_func=print):
    if not api_key: return 0.0
    cached = STATS_CACHE.get(cache_key, {})
    total_net = cached.get("net_deposits", 0.0)
    last_ts = cached.get("last_transfer_ts", 0)
    cursor, latest_ts = None, last_ts
    
    try:
        while True:
            endpoint = f"{API_BASE_URL}/transfers"
            headers = {"Authorization": f"Bearer {api_key}"}
            params = {"cursor": cursor}
            if last_ts > 0: params["start_at"] = last_ts + 1
            
            try:
                resp = requests.get(endpoint, headers=headers, params=params, timeout=10)
            except:
                if PROXY_CONFIG: resp = requests.get(endpoint, headers=headers, params=params, proxies=PROXY_CONFIG, timeout=15)
                else: raise
            
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results: break

            for item in results:
                if item.get("status") == "COMPLETED":
                    amt = float(item.get("amount", 0))
                    direction = item.get("direction", "")
                    ts = int(item.get("created_at", 0))
                    if direction == "IN": total_net += amt
                    elif direction == "OUT": total_net -= amt
                    if ts > latest_ts: latest_ts = ts
            
            cursor = data.get("next")
            if not cursor: break
            
        if cache_key not in STATS_CACHE: STATS_CACHE[cache_key] = {}
        STATS_CACHE[cache_key]["net_deposits"] = total_net
        STATS_CACHE[cache_key]["last_transfer_ts"] = latest_ts
        return total_net
    except Exception as e:
        log_func(f"  [!] Transfer err: {str(e)[:30]}")
        return cached.get("net_deposits", 0.0)

def fetch_fills_incremental(api_key, cache_key, log_func=print):
    if not api_key: return 0.0
    cached = STATS_CACHE.get(cache_key, {})
    if "fills" not in cached: cached["fills"] = []
    
    fills_list = cached["fills"]
    last_ts = cached.get("last_fill_ts", 0)
    cursor, latest_ts = None, last_ts
    new_fills = []
    
    try:
        while True:
            endpoint = f"{API_BASE_URL}/fills"
            headers = {"Authorization": f"Bearer {api_key}"}
            params = {"cursor": cursor, "limit": 100}
            if last_ts > 0: params["start_at"] = last_ts + 1
            
            try:
                resp = requests.get(endpoint, headers=headers, params=params, timeout=10)
            except:
                if PROXY_CONFIG: resp = requests.get(endpoint, headers=headers, params=params, proxies=PROXY_CONFIG, timeout=15)
                else: raise
            
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results: break

            for fill in results:
                price = float(fill.get("price", 0))
                size = float(fill.get("size", 0))
                ts = int(fill.get("created_at", 0))
                vol = price * size
                pnl = float(fill.get("realized_pnl", 0)) - float(fill.get("fee", 0))
                
                new_fills.append({"ts": ts, "vol": vol, "pnl": pnl})
                if ts > latest_ts: latest_ts = ts
            
            cursor = data.get("next")
            if not cursor: break
            
        if new_fills:
            new_fills.sort(key=lambda x: x["ts"])
            fills_list.extend(new_fills)
            if cache_key not in STATS_CACHE: STATS_CACHE[cache_key] = {}
            STATS_CACHE[cache_key]["fills"] = fills_list
            STATS_CACHE[cache_key]["last_fill_ts"] = latest_ts
            STATS_CACHE[cache_key]["total_volume"] = sum(f["vol"] for f in fills_list)
            log_func(f"    + {len(new_fills)} fills")
        
        return cached.get("total_volume", 0.0)
    except Exception as e:
        log_func(f"  [!] Fills err: {str(e)[:30]}")
        return cached.get("total_volume", 0.0)

def fetch_account_summary(api_key):
    if not api_key: return None
    try:
        endpoint = f"{API_BASE_URL}/account/summary"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            resp = requests.get(endpoint, headers=headers, timeout=10)
        except:
            if PROXY_CONFIG: resp = requests.get(endpoint, headers=headers, proxies=PROXY_CONFIG, timeout=10)
            else: raise
        resp.raise_for_status()
        data = resp.json()
        return data[0] if data and isinstance(data, list) else None
    except: return None

def fetch_positions(api_key):
    """
    获取账户当前持仓信息
    """
    if not api_key: return []
    try:
        endpoint = f"{API_BASE_URL}/positions"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            resp = requests.get(endpoint, headers=headers, timeout=10)
        except:
            if PROXY_CONFIG: resp = requests.get(endpoint, headers=headers, proxies=PROXY_CONFIG, timeout=10)
            else: raise
        
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except: return []

def send_tg_msg(message):
    if not TG_BOT_TOKEN or not TG_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}, proxies=PROXY_CONFIG, timeout=15)
    except: pass

# ================= UI 应用程序类 =================

class ParadexStatsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Paradex 统计助手 v5.2 (Fix Excel Addr)")
        self.root.geometry("1100x600")
        
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 10), padding=5)
        
        btn_frame = ttk.Frame(root, padding=10)
        btn_frame.pack(fill=tk.X)
        
        self.btn_total = ttk.Button(btn_frame, text="📊 总资金 (Total Stats)", command=self.run_total_thread)
        self.btn_total.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.btn_weekly = ttk.Button(btn_frame, text="📅 最新周报 + 💾 Excel", command=self.run_weekly_thread)
        self.btn_weekly.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.btn_vol = ttk.Button(btn_frame, text="📉 本周表现 (UTC Fri)", command=self.run_volume_thread)
        self.btn_vol.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.btn_pos = ttk.Button(btn_frame, text="📈 持仓监控 (Positions)", command=self.run_positions_thread)
        self.btn_pos.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.btn_clear = ttk.Button(btn_frame, text="🧹 清屏", command=self.clear_log)
        self.btn_clear.pack(side=tk.RIGHT, padx=5)
        
        self.log_area = scrolledtext.ScrolledText(root, state='disabled', font=("Consolas", 10))
        self.log_area.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        self.log_area.tag_config("INFO", foreground="black")
        self.log_area.tag_config("SUCCESS", foreground="green")
        self.log_area.tag_config("WARNING", foreground="#FF8C00")
        self.log_area.tag_config("ERROR", foreground="red")
        self.log_area.tag_config("HEADER", foreground="blue", font=("Consolas", 10, "bold"))
        self.log_area.tag_config("SUBHEADER", foreground="purple", font=("Consolas", 10, "bold"))
        
        self.log_safe("系统就绪。点击'最新周报'会自动导出Excel。", "INFO")

    def log_safe(self, message, level="INFO"):
        self.root.after(0, lambda: self._log_impl(message, level))

    def _log_impl(self, message, level):
        try:
            self.log_area.configure(state='normal')
            self.log_area.insert(tk.END, message + "\n", level)
            self.log_area.see(tk.END)
            self.log_area.configure(state='disabled')
        except: pass

    def clear_log(self):
        self.log_area.configure(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.configure(state='disabled')

    def toggle_buttons(self, state):
        self.root.after(0, lambda: self._toggle_impl(state))

    def _toggle_impl(self, state):
        s = tk.NORMAL if state else tk.DISABLED
        self.btn_total.config(state=s)
        self.btn_weekly.config(state=s)
        self.btn_vol.config(state=s)
        self.btn_pos.config(state=s)

    # --- Threads ---
    def run_total_thread(self):
        self.toggle_buttons(False)
        self.clear_log()
        threading.Thread(target=self.logic_total_stats, daemon=True).start()

    def run_weekly_thread(self):
        self.toggle_buttons(False)
        self.clear_log()
        threading.Thread(target=self.logic_weekly_stats, daemon=True).start()

    def run_volume_thread(self):
        self.toggle_buttons(False)
        self.clear_log()
        threading.Thread(target=self.logic_volume_stats, daemon=True).start()

    def run_positions_thread(self):
        self.toggle_buttons(False)
        self.clear_log()
        threading.Thread(target=self.logic_positions, daemon=True).start()

    # --- Logic: Total ---
    def logic_total_stats(self):
        self.log_safe("🚀 开始获取实时总资产统计...", "HEADER")
        grand_total_val, grand_total_pnl, grand_total_vol = 0, 0, 0
        tg_msg = "🚀 <b>[Paradex 实时总汇总]</b>\n\n"
        
        for group in GROUPS:
            self.log_safe(f"\nProcessing {group['name']}...", "INFO")
            g_val, g_net, g_vol = 0, 0, 0
            
            for acc in group["accounts"]:
                api_key = acc["key"]
                if not api_key: continue
                cache_key = f"g{group['id']}_{acc['name']}"
                
                self.log_safe(f"  - 更新 {acc['name']}...", "INFO")
                fetch_transfers_incremental(api_key, cache_key, self.log_safe)
                fetch_fills_incremental(api_key, cache_key, self.log_safe)
                summ = fetch_account_summary(api_key)
                
                val = float(summ.get("account_value", 0)) if summ else 0.0
                net = STATS_CACHE.get(cache_key, {}).get("net_deposits", 0.0)
                vol = STATS_CACHE.get(cache_key, {}).get("total_volume", 0.0)
                
                g_val += val
                g_net += net
                g_vol += vol
                
                pnl = val - net
                self.log_safe(f"    余额: ${val:,.0f} | 净充: ${net:,.0f} | 盈亏: ${pnl:,.0f}", "INFO")

            g_pnl = g_val - g_net
            eff = (g_pnl / (g_vol / 1000000)) if g_vol > 0 else 0
            self.log_safe(f"> {group['name']} 汇总: 余额${g_val:,.0f} | 盈亏${g_pnl:,.0f}", "SUCCESS")
            
            tg_msg += f"📦 <b>{group['name']}</b>\n├ 余额: ${g_val:,.0f}\n├ 盈亏: ${g_pnl:,.2f}\n└ 效率: ${eff:,.2f}/M\n\n"
            grand_total_val += g_val
            grand_total_pnl += g_pnl
            grand_total_vol += g_vol

        save_json(CACHE_FILE, STATS_CACHE)
        
        total_eff = (grand_total_pnl / (grand_total_vol / 1000000)) if grand_total_vol > 0 else 0
        summary_str = f"💰 总余额: ${grand_total_val:,.2f}\n💹 总盈亏: ${grand_total_pnl:,.2f}\n📊 总成交: ${grand_total_vol:,.0f}\n⚡ 总效率: ${total_eff:.2f}/M"
        self.log_safe("\n" + "="*40 + "\n" + summary_str, "HEADER")
        
        tg_msg += "━━━━━━━━━━━━━━\n" + summary_str.replace("\n", "\n")
        if TG_BOT_TOKEN:
            send_tg_msg(tg_msg)
            self.log_safe("✅ TG 推送成功", "SUCCESS")
        
        self.toggle_buttons(True)

    # --- Logic: Weekly + XP History + Excel ---
    def logic_weekly_stats(self):
        self.log_safe("📅 开始计算上周统计 & 准备导出 Excel...", "HEADER")
        self.log_safe("[1/2] 更新数据与XP...", "INFO")
        account_data = {}
        total_xp_pool = 0
        total_latest_week_xp = 0
        current_week_num = 0
        
        excel_rows = []

        for group in GROUPS:
            for acc in group["accounts"]:
                api_key = acc["key"]
                if not api_key: continue
                cache_key = f"g{group['id']}_{acc['name']}"
                
                self.log_safe(f"  Checking {acc['name']}...", "INFO")
                # 更新交易数据
                fetch_fills_incremental(api_key, cache_key, lambda x: None)
                summ = fetch_account_summary(api_key)
                balance = float(summ.get("account_value", 0)) if summ else 0.0
                
                # 获取 XP & Address (统一调用一次)
                xp_total, xp_week, week_num, xp_earned, xp_avail = fetch_xp_combined(api_key)
                full_address = fetch_address_unified(api_key) # [修复] 只获取一次原始地址

                if week_num > current_week_num:
                    current_week_num = week_num
                
                account_data[cache_key] = {
                    "balance": balance, 
                    "xp": xp_total, 
                    "xp_week": xp_week,
                    "week_num": week_num,
                    "xp_earned": xp_earned, 
                    "xp_avail": xp_avail,
                    "full_address": full_address
                }
                total_xp_pool += xp_total
                total_latest_week_xp += xp_week
        
        save_json(CACHE_FILE, STATS_CACHE)

        self.log_safe(f"\n[2/2] 统计汇总 (最新已结算周: Week {current_week_num})", "INFO")
        
        now = datetime.now()
        this_friday_8am = (now - timedelta(days=(now.weekday() - 4) % 7)).replace(hour=8, minute=0, second=0, microsecond=0)
        if now < this_friday_8am: end = this_friday_8am - timedelta(days=7)
        else: end = this_friday_8am
        start = end - timedelta(days=7)
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        
        tot_vol, tot_pnl, tot_cnt = 0, 0, 0
        
        for key, data in sorted(STATS_CACHE.items()):
            fills = data.get("fills", [])
            weekly_fills = [f for f in fills if start_ms <= f["ts"] < end_ms]
            
            vol = sum(f["vol"] for f in weekly_fills)
            pnl = sum(f["pnl"] for f in weekly_fills)
            count = len(weekly_fills)
            
            acc_info = account_data.get(key, {})
            if not acc_info: continue

            # 准备数据
            raw_addr = acc_info.get("full_address", "")
            # UI 显示用的短地址
            short_addr = f"{raw_addr[:6]}...{raw_addr[-4:]}" if len(raw_addr) > 10 else (raw_addr or "No Addr")
            
            # UI 输出
            week_label = f"W{acc_info['week_num']}" if acc_info['week_num'] > 0 else "W--"
            xp_str = f"Tot:{acc_info['xp']:.0f} (Earn:{acc_info['xp_earned']:.0f} | Avail:{acc_info['xp_avail']:.0f} | {week_label}:+{acc_info['xp_week']:.0f})"
            res_str = f"• {key} [{short_addr}]: ${acc_info['balance']:,.0f} | XP: {xp_str} | Vol ${vol:,.0f} | PnL ${pnl:+.2f}"
            self.log_safe(res_str, "INFO")
            
            # Excel 数据收集 (写入完整地址)
            excel_rows.append({
                "Account": key,
                "Address": raw_addr,  # 完整地址
                "Balance ($)": acc_info['balance'],
                "Total XP": acc_info['xp'],
                "Earned XP": acc_info['xp_earned'],
                "Available XP": acc_info['xp_avail'],
                "Latest Week": f"Week {acc_info['week_num']}",
                "Week XP Gained": acc_info['xp_week'],
                "Week Volume ($)": vol,
                "Week PnL ($)": pnl,
                "Trades Count": count
            })

            tot_vol += vol
            tot_pnl += pnl
            tot_cnt += count

        tot_eff = (tot_pnl / (tot_vol / 1000000)) if tot_vol > 0 else 0
        summary = f"\n📊 交易周汇总 ({start.strftime('%m-%d')}~{end.strftime('%m-%d')}):\n交易笔数: {tot_cnt}\n周成交额: ${tot_vol:,.0f}\n周总盈亏: ${tot_pnl:+.2f}\n资金效率: ${tot_eff:.2f}/M\n\n⭐ XP官方数据:\n总 XP池: {total_xp_pool:,.0f}\n最新周(Week {current_week_num})增量: +{total_latest_week_xp:,.0f}"
        self.log_safe(summary, "SUCCESS")
        
        # --- 导出 Excel ---
        try:
            if excel_rows:
                if not os.path.exists(EXCEL_DIR):
                    os.makedirs(EXCEL_DIR)
                
                df = pd.DataFrame(excel_rows)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"paradex_report_{timestamp}.xlsx"
                filepath = os.path.join(EXCEL_DIR, filename)
                
                df.to_excel(filepath, index=False)
                self.log_safe(f"\n💾 Excel 已成功保存: {filepath}", "SUCCESS")
            else:
                self.log_safe("\n⚠️ 没有数据可导出。", "WARNING")
        except Exception as e:
            self.log_safe(f"\n❌ Excel 导出失败: {e}", "ERROR")

        self.toggle_buttons(True)

    # --- Logic: Volume Stats (Real-time PnL/Eff) ---
    def logic_volume_stats(self):
        self.log_safe("📈 开始计算本周表现 (Since UTC Friday 00:00)...", "HEADER")
        
        now_utc = datetime.now(timezone.utc)
        diff = (now_utc.weekday() - 4) % 7
        last_friday = now_utc - timedelta(days=diff)
        start_date = last_friday.replace(hour=0, minute=0, second=0, microsecond=0)
        start_ms = int(start_date.timestamp() * 1000)
        
        self.log_safe(f"🕒 统计起始时间 (UTC): {start_date.strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        self.log_safe("-" * 50, "INFO")

        grand_total_vol = 0
        grand_total_pnl = 0
        
        for group in GROUPS:
            g_vol, g_pnl = 0, 0
            self.log_safe(f"Processing {group['name']}...", "INFO")
            
            for acc in group["accounts"]:
                api_key = acc["key"]
                if not api_key: continue
                cache_key = f"g{group['id']}_{acc['name']}"
                
                fetch_fills_incremental(api_key, cache_key, lambda x: None)
                cached = STATS_CACHE.get(cache_key, {})
                fills = cached.get("fills", [])
                
                weekly_fills = [f for f in fills if f["ts"] >= start_ms]
                
                acc_vol = sum(f["vol"] for f in weekly_fills)
                acc_pnl = sum(f["pnl"] for f in weekly_fills)
                
                g_vol += acc_vol
                g_pnl += acc_pnl
                
                self.log_safe(f"  - {acc['name']}: Vol ${acc_vol:,.0f} | PnL ${acc_pnl:+.2f}", "INFO")
            
            g_eff = (g_pnl / (g_vol / 1000000)) if g_vol > 0 else 0
            res_str = f"> {group['name']} 合计: Vol ${g_vol:,.0f} | PnL ${g_pnl:+.2f} | 效率 ${g_eff:.2f}/M"
            self.log_safe(res_str, "SUBHEADER")
            self.log_safe("", "INFO")
            
            grand_total_vol += g_vol
            grand_total_pnl += g_pnl

        grand_eff = (grand_total_pnl / (grand_total_vol / 1000000)) if grand_total_vol > 0 else 0
        summary = f"\n📊 本周全账户汇总 (UTC Fri~Now):\n----------------------------------\n💰 总交易量: ${grand_total_vol:,.0f}\n📉 总盈亏额: ${grand_total_pnl:+.2f}\n⚡ 资金效率: ${grand_eff:.2f}/M"
        self.log_safe("=" * 50, "HEADER")
        self.log_safe(summary, "HEADER")
        
        self.toggle_buttons(True)

    # --- Logic: Positions (持仓监控) ---
    def logic_positions(self):
        self.log_safe("🔍 开始扫描全账户持仓...", "HEADER")
        
        total_upnl = 0.0  # 总未结盈亏
        total_notional = 0.0 # 总持仓名义价值
        has_position = False

        for group in GROUPS:
            self.log_safe(f"Checking {group['name']}...", "INFO")
            group_upnl = 0.0
            
            for acc in group["accounts"]:
                api_key = acc["key"]
                if not api_key: continue
                
                positions = fetch_positions(api_key)
                active_positions = [p for p in positions if float(p.get("size", 0)) != 0]
                
                if active_positions:
                    has_position = True
                    for pos in active_positions:
                        market = pos.get("market", "Unknown")
                        size = float(pos.get("size", 0))
                        side = pos.get("side", "LONG" if size > 0 else "SHORT")
                        entry_price = float(pos.get("average_entry_price", 0))
                        upnl = float(pos.get("unrealized_pnl", 0))
                        
                        group_upnl += upnl
                        total_upnl += upnl
                        total_notional += abs(size * entry_price)

                        tag = "SUCCESS" if upnl >= 0 else "ERROR"
                        self.log_safe(
                            f"  [{acc['name']}] {market} | {side} {abs(size):.3f} | Entry: {entry_price:,.2f} | uPnL: ${upnl:+.2f}", 
                            tag
                        )
            
            if group_upnl != 0:
                self.log_safe(f"  > {group['name']} 未结盈亏: ${group_upnl:+.2f}\n", "SUBHEADER")

        if not has_position:
            self.log_safe("\n✅ 当前没有任何持仓。", "SUCCESS")
        else:
            self.log_safe("=" * 40, "HEADER")
            summary = f"📊 持仓汇总:\n💰 总未结盈亏 (uPnL): ${total_upnl:+.2f}\n📜 总持仓名义价值 (Est): ${total_notional:,.0f}"
            self.log_safe(summary, "HEADER" if total_upnl >= 0 else "ERROR")

        self.toggle_buttons(True)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ParadexStatsApp(root)
        root.mainloop()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        input("Press Enter to exit...")