import json
import os
import uuid
import shutil
from datetime import datetime, timedelta
import pandas as pd


TICKETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tickets.json")
ATTACHMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attachments")

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
MAX_FILE_SIZE_MB = 5
MAX_ATTACHMENTS_PER_TICKET = 3

TICKET_STATUSES = ["待处理", "处理中", "已解决", "已关闭"]
TICKET_PRIORITIES = ["低", "中", "高", "紧急"]
DEFAULT_ASSIGNEES = ["张三", "李四", "王五", "赵六", "未分配"]


def init_attachments_dir():
    if not os.path.exists(ATTACHMENTS_DIR):
        os.makedirs(ATTACHMENTS_DIR, exist_ok=True)


def is_allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_file_extension(filename):
    return os.path.splitext(filename)[1].lower()


def save_attachment(file_obj, original_filename, ticket_id):
    init_attachments_dir()

    if not is_allowed_file(original_filename):
        raise ValueError(f"不支持的文件类型，仅支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    file_size_mb = len(file_obj.getvalue()) / (1024 * 1024) if hasattr(file_obj, 'getvalue') else os.path.getsize(file_obj) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"文件大小超过限制，最大允许 {MAX_FILE_SIZE_MB}MB")

    ticket_dir = os.path.join(ATTACHMENTS_DIR, ticket_id)
    os.makedirs(ticket_dir, exist_ok=True)

    ext = get_file_extension(original_filename)
    safe_name = f"{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    file_path = os.path.join(ticket_dir, safe_name)

    if hasattr(file_obj, 'seek'):
        file_obj.seek(0)
    with open(file_path, 'wb') as f:
        if hasattr(file_obj, 'read'):
            f.write(file_obj.read())
        else:
            with open(file_obj, 'rb') as src:
                f.write(src.read())

    return {
        "attachment_id": str(uuid.uuid4())[:8],
        "original_name": original_filename,
        "stored_name": safe_name,
        "file_size": round(file_size_mb, 2),
        "file_type": ext.lstrip(".").upper(),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_attachment_path(ticket_id, stored_name):
    return os.path.join(ATTACHMENTS_DIR, ticket_id, stored_name)


def get_ticket_attachments(ticket):
    return ticket.get("attachments", [])

STATUS_COLOR_MAP = {
    "待处理": "#FFA15A",
    "处理中": "#636EFA",
    "已解决": "#00CC96",
    "已关闭": "#AB63FA"
}

PRIORITY_COLOR_MAP = {
    "低": "#00CC96",
    "中": "#636EFA",
    "高": "#FFA15A",
    "紧急": "#EF553B"
}

STATUS_TRANSITIONS = {
    "待处理": ["处理中", "已关闭"],
    "处理中": ["待处理", "已解决", "已关闭"],
    "已解决": ["处理中", "已关闭"],
    "已关闭": []
}


def load_tickets():
    if not os.path.exists(TICKETS_FILE):
        return []
    try:
        with open(TICKETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_tickets(tickets):
    with open(TICKETS_FILE, "w", encoding="utf-8") as f:
        json.dump(tickets, f, ensure_ascii=False, indent=2)


def generate_ticket_id():
    return f"TKT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def create_ticket_from_feedback(feedback_id, feedback_content, feedback_type,
                                assignee="未分配", priority="中",
                                due_date=None, notes="", attachments=None):
    if due_date is None:
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    if attachments is None:
        attachments = []

    ticket_id = generate_ticket_id()
    saved_attachments = []

    for att_info in attachments:
        try:
            saved = save_attachment(
                att_info["file_obj"],
                att_info["original_name"],
                ticket_id
            )
            saved_attachments.append(saved)
        except ValueError:
            raise

    history_details = f"从反馈创建工单，类型: {feedback_type}"
    if saved_attachments:
        history_details += f"，附带 {len(saved_attachments)} 个附件"

    ticket = {
        "ticket_id": ticket_id,
        "feedback_id": feedback_id,
        "feedback_content": feedback_content,
        "feedback_type": feedback_type,
        "title": feedback_content[:30] + ("..." if len(feedback_content) > 30 else ""),
        "status": "待处理",
        "assignee": assignee,
        "priority": priority,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "due_date": due_date,
        "notes": notes,
        "attachments": saved_attachments,
        "comments": [],
        "history": [
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "创建工单",
                "details": history_details
            }
        ]
    }

    tickets = load_tickets()
    tickets.append(ticket)
    save_tickets(tickets)
    return ticket


def update_ticket(ticket_id, **kwargs):
    tickets = load_tickets()
    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            old_status = ticket.get("status", "")
            for key, value in kwargs.items():
                if key in ticket:
                    ticket[key] = value
            ticket["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if "status" in kwargs and kwargs["status"] != old_status:
                ticket["history"].append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "action": "状态变更",
                    "details": f"{old_status} → {kwargs['status']}"
                })
            if "assignee" in kwargs:
                ticket["history"].append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "action": "分配处理人",
                    "details": f"分配给: {kwargs['assignee']}"
                })
            if "priority" in kwargs:
                ticket["history"].append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "action": "优先级变更",
                    "details": f"优先级: {kwargs['priority']}"
                })
            if "notes" in kwargs:
                ticket["history"].append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "action": "更新备注",
                    "details": "备注信息已更新"
                })

            save_tickets(tickets)
            return ticket
    return None


def get_ticket(ticket_id):
    tickets = load_tickets()
    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            return ticket
    return None


def delete_ticket(ticket_id):
    tickets = load_tickets()
    tickets = [t for t in tickets if t["ticket_id"] != ticket_id]
    save_tickets(tickets)

    ticket_dir = os.path.join(ATTACHMENTS_DIR, ticket_id)
    if os.path.exists(ticket_dir):
        shutil.rmtree(ticket_dir)


def add_ticket_note(ticket_id, note):
    tickets = load_tickets()
    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            if ticket["notes"]:
                ticket["notes"] += f"\n\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n{note}"
            else:
                ticket["notes"] = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n{note}"
            ticket["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ticket["history"].append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "添加备注",
                "details": note[:50] + ("..." if len(note) > 50 else "")
            })
            save_tickets(tickets)
            return ticket
    return None


def add_ticket_comment(ticket_id, commenter, content):
    tickets = load_tickets()
    for ticket in tickets:
        if ticket["ticket_id"] == ticket_id:
            if "comments" not in ticket:
                ticket["comments"] = []
            comment = {
                "comment_id": str(uuid.uuid4())[:8],
                "commenter": commenter,
                "content": content,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            ticket["comments"].append(comment)
            ticket["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ticket["history"].append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "添加评论",
                "details": f"{commenter}: {content[:50]}" + ("..." if len(content) > 50 else "")
            })
            save_tickets(tickets)
            return ticket
    return None


def get_ticket_comments(ticket_id):
    ticket = get_ticket(ticket_id)
    if not ticket:
        return []
    comments = ticket.get("comments", [])
    return sorted(comments, key=lambda c: c["created_at"], reverse=True)


def get_available_status_transitions(current_status):
    return STATUS_TRANSITIONS.get(current_status, [])


def filter_tickets(tickets, status=None, priority=None, assignee=None,
                   date_from=None, date_to=None, search_keyword=None):
    filtered = tickets.copy()

    if status:
        filtered = [t for t in filtered if t["status"] in status]
    if priority:
        filtered = [t for t in filtered if t["priority"] in priority]
    if assignee:
        filtered = [t for t in filtered if t["assignee"] in assignee]
    if date_from:
        date_from_str = date_from.strftime("%Y-%m-%d")
        filtered = [t for t in filtered if t["created_at"][:10] >= date_from_str]
    if date_to:
        date_to_str = date_to.strftime("%Y-%m-%d")
        filtered = [t for t in filtered if t["created_at"][:10] <= date_to_str]
    if search_keyword:
        keyword = search_keyword.lower()
        filtered = [
            t for t in filtered
            if keyword in t["ticket_id"].lower()
            or keyword in t["title"].lower()
            or keyword in t["feedback_content"].lower()
            or keyword in t.get("notes", "").lower()
        ]

    return filtered


def tickets_to_dataframe(tickets):
    if not tickets:
        return pd.DataFrame(columns=[
            "工单编号", "标题", "状态", "优先级", "处理人",
            "创建时间", "截止日期", "反馈类型"
        ])

    data = []
    for t in tickets:
        data.append({
            "工单编号": t["ticket_id"],
            "标题": t["title"],
            "状态": t["status"],
            "优先级": t["priority"],
            "处理人": t["assignee"],
            "创建时间": t["created_at"],
            "截止日期": t["due_date"],
            "反馈类型": t["feedback_type"]
        })
    return pd.DataFrame(data)


def get_ticket_statistics(tickets):
    if not tickets:
        return {
            "total": 0,
            "pending": 0,
            "processing": 0,
            "resolved": 0,
            "closed": 0,
            "overdue": 0
        }

    now = datetime.now().strftime("%Y-%m-%d")
    stats = {
        "total": len(tickets),
        "pending": len([t for t in tickets if t["status"] == "待处理"]),
        "processing": len([t for t in tickets if t["status"] == "处理中"]),
        "resolved": len([t for t in tickets if t["status"] == "已解决"]),
        "closed": len([t for t in tickets if t["status"] == "已关闭"]),
        "overdue": len([
            t for t in tickets
            if t["status"] not in ["已关闭", "已解决"] and t["due_date"] < now
        ])
    }
    return stats


def is_feedback_converted(feedback_id):
    tickets = load_tickets()
    return any(t.get("feedback_id") == feedback_id for t in tickets)


def get_ticket_by_feedback(feedback_id):
    tickets = load_tickets()
    for t in tickets:
        if t.get("feedback_id") == feedback_id:
            return t
    return None
