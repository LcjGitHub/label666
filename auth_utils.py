import json
import os
import hashlib
import streamlit as st
import pandas as pd
from datetime import datetime

USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")
LOGIN_LOGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login_logs.json")


def hash_password(password):
    return "sha256:" + hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, stored_hash):
    if stored_hash.startswith("sha256:"):
        return stored_hash == hash_password(password)
    return stored_hash == password


def load_users_data():
    if not os.path.exists(USERS_FILE):
        return {"roles": {}, "users": []}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"roles": {}, "users": []}


def save_users_data(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_login_logs():
    if not os.path.exists(LOGIN_LOGS_FILE):
        return []
    try:
        with open(LOGIN_LOGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_login_logs(logs):
    with open(LOGIN_LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def add_login_log(username, ip_address, success, message=""):
    logs = load_login_logs()
    log_entry = {
        "id": f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}",
        "username": username,
        "login_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip_address": ip_address,
        "success": success,
        "message": message
    }
    logs.insert(0, log_entry)
    save_login_logs(logs)
    return log_entry


def get_login_logs_by_username(username, limit=None):
    logs = load_login_logs()
    user_logs = [log for log in logs if log["username"] == username]
    if limit:
        return user_logs[:limit]
    return user_logs


def get_client_ip():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx and hasattr(ctx, 'session'):
            session = ctx.session
            if hasattr(session, '_request'):
                request = session._request
                if hasattr(request, 'headers'):
                    x_forwarded_for = request.headers.get('X-Forwarded-For')
                    if x_forwarded_for:
                        return x_forwarded_for.split(',')[0].strip()
                    return request.headers.get('X-Real-IP', '127.0.0.1')
    except Exception:
        pass
    return "127.0.0.1"


def get_roles():
    data = load_users_data()
    return data.get("roles", {})


def get_role_name(role_key):
    roles = get_roles()
    return roles.get(role_key, {}).get("name", role_key)


def get_role_permissions(role_key):
    roles = get_roles()
    return roles.get(role_key, {}).get("permissions", [])


def get_users():
    data = load_users_data()
    return data.get("users", [])


def get_user(username):
    users = get_users()
    for user in users:
        if user["username"] == username:
            return user
    return None


def authenticate(username, password):
    user = get_user(username)
    if user and verify_password(password, user["password"]):
        return user
    return None


def update_last_login(username):
    data = load_users_data()
    for user in data.get("users", []):
        if user["username"] == username:
            user["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_users_data(data)
            break


def init_session():
    if "_auth_initialized" not in st.session_state:
        if "user" not in st.session_state:
            st.session_state.user = None
        st.session_state._auth_initialized = True


def is_logged_in():
    init_session()
    return st.session_state.user is not None


def get_current_user():
    if is_logged_in():
        return st.session_state.user
    return None


def get_current_role():
    user = get_current_user()
    if user:
        return user.get("role")
    return None


def has_permission(permission):
    user = get_current_user()
    if not user:
        return False
    role = user.get("role")
    permissions = get_role_permissions(role)
    return permission in permissions


def require_permission(permission):
    if not has_permission(permission):
        role_name = get_role_name(get_current_role()) if get_current_role() else "未登录"
        st.error(f"⚠️ 权限不足！您当前的角色是「{role_name}」，此操作需要更高权限。")
        return False
    return True


def login(username, password):
    user = authenticate(username, password)
    ip_address = get_client_ip()
    if user:
        st.session_state.user = {
            "username": user["username"],
            "full_name": user.get("full_name", user["username"]),
            "email": user.get("email", ""),
            "role": user["role"]
        }
        update_last_login(username)
        add_login_log(username, ip_address, True, "登录成功")
        return True
    add_login_log(username, ip_address, False, "用户名或密码错误")
    return False


def logout():
    init_session()
    st.session_state.user = None
    for key in list(st.session_state.keys()):
        if key.startswith("report_") or key.startswith("filter_") or key.startswith("show_"):
            del st.session_state[key]


def add_user(username, password, role, full_name="", email=""):
    if get_user(username):
        return False, "用户名已存在"
    data = load_users_data()
    new_user = {
        "username": username,
        "password": hash_password(password),
        "role": role,
        "full_name": full_name or username,
        "email": email,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_login": None
    }
    data["users"].append(new_user)
    save_users_data(data)
    return True, "用户创建成功"


def update_user(username, password=None, role=None, full_name=None, email=None):
    data = load_users_data()
    for user in data.get("users", []):
        if user["username"] == username:
            if password is not None:
                user["password"] = hash_password(password)
            if role is not None:
                user["role"] = role
            if full_name is not None:
                user["full_name"] = full_name
            if email is not None:
                user["email"] = email
            save_users_data(data)
            return True, "用户信息更新成功"
    return False, "用户不存在"


def delete_user(username):
    if username == "admin":
        return False, "不能删除管理员账户"
    data = load_users_data()
    original_count = len(data.get("users", []))
    data["users"] = [u for u in data.get("users", []) if u["username"] != username]
    if len(data["users"]) < original_count:
        save_users_data(data)
        return True, "用户删除成功"
    return False, "用户不存在"


def render_login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 用户登录</h1>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h3 style='text-align: center;'>欢迎使用用户反馈分析系统</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #888;'>请登录后继续使用系统功能</p>", unsafe_allow_html=True)
        st.markdown("---")

        with st.form("login_form"):
            username = st.text_input("👤 用户名", placeholder="请输入用户名")
            password = st.text_input("🔒 密码", type="password", placeholder="请输入密码")

            col_login, col_forgot = st.columns([2, 1])
            with col_login:
                submitted = st.form_submit_button("✅ 登录", use_container_width=True, type="primary")
            with col_forgot:
                if st.form_submit_button("❓ 忘记密码", use_container_width=True):
                    st.info("请联系管理员重置密码")

            if submitted:
                if not username or not password:
                    st.error("请输入用户名和密码")
                else:
                    if login(username, password):
                        st.success(f"欢迎回来，{get_current_user()['full_name']}！")
                        st.rerun()
                    else:
                        st.error("用户名或密码错误，请重试")


def render_user_info_in_sidebar():
    if not is_logged_in():
        return

    user = get_current_user()
    role_name = get_role_name(user["role"])

    st.markdown("---")
    st.markdown("### 👤 当前用户")
    st.markdown(f"**姓名**: {user['full_name']}")
    st.markdown(f"**用户名**: `{user['username']}`")
    st.markdown(f"**角色**: :blue[{role_name}]")
    if user.get("email"):
        st.markdown(f"**邮箱**: {user['email']}")

    role_permissions = get_role_permissions(user["role"])
    if role_permissions:
        with st.expander("📋 权限列表"):
            permission_names = {
                "view_data": "查看数据",
                "view_dashboard": "查看仪表盘",
                "edit_config": "修改配置",
                "export_data": "导出数据",
                "manage_tickets": "管理工单",
                "manage_users": "管理用户"
            }
            for perm in role_permissions:
                st.markdown(f"- ✅ {permission_names.get(perm, perm)}")

    st.markdown("---")
    if st.button("🚪 退出登录", use_container_width=True):
        logout()
        st.rerun()


def render_user_management_page():
    if not require_permission("manage_users"):
        return

    st.title("👥 用户管理")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📋 用户列表", "➕ 添加用户", "🔧 角色权限"])

    with tab1:
        st.subheader("用户列表")
        users = get_users()
        roles = get_roles()

        if not users:
            st.info("暂无用户数据")
        else:
            user_data = []
            for u in users:
                user_data.append({
                    "用户名": u["username"],
                    "姓名": u.get("full_name", ""),
                    "邮箱": u.get("email", ""),
                    "角色": roles.get(u["role"], {}).get("name", u["role"]),
                    "创建时间": u.get("created_at", ""),
                    "最后登录": u.get("last_login", "从未登录")
                })
            df = pd.DataFrame(user_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("用户操作")

        col_edit, col_delete, col_logs = st.columns(3)
        with col_edit:
            edit_username = st.selectbox(
                "选择要编辑的用户",
                [u["username"] for u in users],
                key="edit_user_select"
            )
            if edit_username:
                edit_user = get_user(edit_username)
                if edit_user:
                    with st.form("edit_user_form"):
                        new_full_name = st.text_input("姓名", value=edit_user.get("full_name", ""))
                        new_email = st.text_input("邮箱", value=edit_user.get("email", ""))
                        role_options = list(roles.keys())
                        new_role = st.selectbox(
                            "角色",
                            role_options,
                            index=role_options.index(edit_user["role"]) if edit_user["role"] in role_options else 0,
                            format_func=lambda r: roles.get(r, {}).get("name", r)
                        )
                        new_password = st.text_input("重置密码（留空不修改）", type="password")

                        if st.form_submit_button("💾 保存修改", use_container_width=True, type="primary"):
                            success, msg = update_user(
                                edit_username,
                                password=new_password if new_password else None,
                                role=new_role,
                                full_name=new_full_name,
                                email=new_email
                            )
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

        with col_delete:
            delete_username = st.selectbox(
                "选择要删除的用户",
                [u["username"] for u in users if u["username"] != "admin"],
                key="delete_user_select"
            )
            if delete_username:
                st.warning(f"⚠️ 确定要删除用户「{delete_username}」吗？此操作不可恢复！")
                if st.button("🗑️ 确认删除", use_container_width=True, type="secondary"):
                    success, msg = delete_user(delete_username)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with col_logs:
            log_username = st.selectbox(
                "选择查看登录日志的用户",
                [u["username"] for u in users],
                key="log_user_select"
            )
            if log_username:
                log_user = get_user(log_username)
                log_count = len(get_login_logs_by_username(log_username))
                st.info(f"该用户共有 {log_count} 条登录记录")
                if st.button("📋 查看登录日志", use_container_width=True, type="primary"):
                    st.session_state[f"show_login_logs_{log_username}"] = True

        if any(st.session_state.get(f"show_login_logs_{u['username']}", False) for u in users):
            for u in users:
                if st.session_state.get(f"show_login_logs_{u['username']}", False):
                    target_user = u
                    break
            with st.expander(f"📋 {target_user.get('full_name', target_user['username'])} 的登录日志", expanded=True):
                login_logs = get_login_logs_by_username(target_user["username"])
                if not login_logs:
                    st.info("暂无登录记录")
                else:
                    log_data = []
                    for log in login_logs:
                        log_data.append({
                            "登录时间": log["login_time"],
                            "登录IP": log["ip_address"],
                            "登录状态": "✅ 成功" if log["success"] else "❌ 失败",
                            "备注": log.get("message", "")
                        })
                    log_df = pd.DataFrame(log_data)
                    st.dataframe(log_df, use_container_width=True, hide_index=True)

                    success_count = sum(1 for log in login_logs if log["success"])
                    fail_count = len(login_logs) - success_count
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("总登录次数", len(login_logs))
                    with col2:
                        st.metric("成功次数", success_count)
                    with col3:
                        st.metric("失败次数", fail_count)

                if st.button("关闭日志", key=f"close_logs_{target_user['username']}", use_container_width=True):
                    st.session_state[f"show_login_logs_{target_user['username']}"] = False
                    st.rerun()

    with tab2:
        st.subheader("添加新用户")
        roles = get_roles()

        with st.form("add_user_form"):
            new_username = st.text_input("用户名 *", placeholder="请输入用户名")
            new_password = st.text_input("密码 *", type="password", placeholder="请输入密码")
            new_full_name = st.text_input("姓名", placeholder="请输入用户姓名")
            new_email = st.text_input("邮箱", placeholder="请输入邮箱地址")
            role_options = list(roles.keys())
            new_role = st.selectbox(
                "角色 *",
                role_options,
                format_func=lambda r: roles.get(r, {}).get("name", r)
            )

            col_submit, col_reset = st.columns(2)
            with col_submit:
                if st.form_submit_button("✅ 创建用户", use_container_width=True, type="primary"):
                    if not new_username or not new_password:
                        st.error("请填写必填项（用户名和密码）")
                    else:
                        success, msg = add_user(
                            new_username,
                            new_password,
                            new_role,
                            full_name=new_full_name,
                            email=new_email
                        )
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
            with col_reset:
                if st.form_submit_button("🔄 重置", use_container_width=True):
                    st.rerun()

    with tab3:
        st.subheader("角色权限配置")
        roles = get_roles()

        permission_info = {
            "view_data": {"name": "查看数据", "desc": "查看基础数据和报表"},
            "view_dashboard": {"name": "查看仪表盘", "desc": "访问分析仪表盘页面"},
            "edit_config": {"name": "修改配置", "desc": "修改系统配置和报告设置"},
            "export_data": {"name": "导出数据", "desc": "导出PDF和Excel报告、下载图表"},
            "manage_tickets": {"name": "管理工单", "desc": "创建、编辑、删除工单"},
            "manage_users": {"name": "管理用户", "desc": "添加、编辑、删除用户账户"}
        }

        for role_key, role_info in roles.items():
            with st.expander(f"🎭 {role_info.get('name', role_key)}", expanded=(role_key == "admin")):
                st.markdown(f"**角色标识**: `{role_key}`")
                st.markdown("**权限列表**:")
                for perm in role_info.get("permissions", []):
                    perm_info = permission_info.get(perm, {"name": perm, "desc": ""})
                    st.markdown(f"- ✅ **{perm_info['name']}** - {perm_info['desc']}")

                missing_perms = [p for p in permission_info.keys() if p not in role_info.get("permissions", [])]
                if missing_perms:
                    st.markdown("**未拥有权限**:")
                    for perm in missing_perms:
                        perm_info = permission_info.get(perm, {"name": perm, "desc": ""})
                        st.markdown(f"- ❌ **{perm_info['name']}** - {perm_info['desc']}")
