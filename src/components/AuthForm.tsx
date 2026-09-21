"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { Leaf, LockKeyhole, Eye, EyeOff } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { bootstrapTraceAdmin, getTraceAuthStatus, TraceRole } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const params = useSearchParams();
  const auth = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [initialized, setInitialized] = useState<boolean | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const [form, setForm] = useState({
    username: "",
    password: "",
    display_name: "",
    organization: "",
    role: "farmer" as Exclude<TraceRole, "admin" | "admin_hq">,
  });

  useEffect(() => {
    if (mode === "register") {
      void getTraceAuthStatus()
        .then((x) => setInitialized(x.initialized))
        .catch(() => setInitialized(true));
    }
  }, [mode]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");

    try {
      if (mode === "login") {
        await auth.login(form.username.trim(), form.password);
        router.replace(params.get("next") || "/");
      } else if (initialized === false) {
        const x = await bootstrapTraceAdmin(form);
        localStorage.setItem("caymit_access_token", x.access_token);
        localStorage.setItem("trace_token", x.access_token);
        window.location.href = "/";
      } else {
        await auth.register(form);
        router.replace("/login?registered=1");
      }
    } catch (err: any) {
      console.error("Auth error:", err);
      const serverMsg =
        err?.response?.data?.error?.details ||
        err?.response?.data?.error?.message_key ||
        err?.response?.data?.detail ||
        (err?.response?.status === 401
          ? "Tên đăng nhập hoặc mật khẩu không chính xác."
          : "Không thể kết nối đến máy chủ xác thực. Vui lòng kiểm tra lại.");
      setError(serverMsg);
    } finally {
      setBusy(false);
    }
  };

  const firstAdmin = mode === "register" && initialized === false;

  return (
    <main className="flex min-h-dvh items-center justify-center bg-gray-950 p-4 font-sans">
      <div className="w-full max-w-md rounded-3xl border border-gray-800 bg-gray-900 p-6 shadow-2xl sm:p-8">
        <div className="mb-7 flex items-center gap-3">
          <div className="rounded-2xl bg-emerald-500 p-3 shadow-lg shadow-emerald-500/20">
            <Leaf className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-black text-white">CayMit AI</h1>
            <p className="text-sm text-gray-500">Quản lý vườn mít thông minh</p>
          </div>
        </div>

        <h2 className="text-2xl font-bold text-white">
          {mode === "login"
            ? "Đăng nhập"
            : firstAdmin
            ? "Khởi tạo quản trị viên"
            : "Tạo tài khoản"}
        </h2>
        <p className="mt-1 text-sm text-gray-400">
          {mode === "login"
            ? "Tiếp tục vào không gian vận hành của bạn."
            : firstAdmin
            ? "Đây là tài khoản đầu tiên và sẽ quản trị toàn bộ hệ thống."
            : "Chọn đúng vai trò để hệ thống cấp quyền nghiệp vụ."}
        </p>

        <form onSubmit={submit} className="mt-6 space-y-4">
          {mode === "register" && (
            <>
              <Field
                label="Họ và tên"
                value={form.display_name}
                set={(v) => setForm({ ...form, display_name: v })}
                placeholder="Nguyễn Văn A"
              />
              <Field
                label="Đơn vị / tổ chức"
                value={form.organization}
                set={(v) => setForm({ ...form, organization: v })}
                placeholder="HTX Nông Nghiệp Tam Mỹ"
              />
              {!firstAdmin && (
                <label className="block text-sm font-semibold text-gray-300">
                  Vai trò
                  <select
                    value={form.role}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        role: e.target.value as Exclude<TraceRole, "admin" | "admin_hq">,
                      })
                    }
                    className="mt-2 min-h-12 w-full rounded-xl border border-gray-700 bg-gray-950 px-4 text-white focus:border-emerald-400 outline-none"
                  >
                    <option value="farmer">Nông hộ / Hợp tác xã</option>
                    <option value="technician">Kỹ thuật viên Thẩm định</option>
                    <option value="packhouse_lead">Sơ chế / Đóng gói</option>
                    <option value="logistics">Logistics / Xuất khẩu</option>
                  </select>
                </label>
              )}
            </>
          )}

          <Field
            label="Tên đăng nhập"
            value={form.username}
            set={(v) => setForm({ ...form, username: v })}
            placeholder="admin_tammy hoặc farmer_ba_tam"
          />

          {/* Password Field with Eye Toggle Icon */}
          <div className="space-y-1.5">
            <label className="block text-sm font-semibold text-gray-300">
              Mật khẩu (tối thiểu 8 ký tự)
            </label>
            <div className="relative flex items-center">
              <input
                required
                minLength={8}
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Nhập mật khẩu..."
                className="min-h-12 w-full rounded-xl border border-gray-700 bg-gray-950 pl-4 pr-12 text-white outline-none focus:border-emerald-400 transition"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white transition"
                aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                title={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5 text-emerald-400" />
                ) : (
                  <Eye className="h-5 w-5 text-gray-400" />
                )}
              </button>
            </div>
          </div>

          {error && (
            <p
              role="alert"
              className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300 font-medium"
            >
              {error}
            </p>
          )}

          <button
            disabled={busy || (initialized === null && mode === "register")}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 font-bold text-white shadow-lg shadow-emerald-500/20 hover:bg-emerald-400 disabled:opacity-50 transition"
          >
            <LockKeyhole className="h-4 w-4" />
            {busy
              ? "Đang xử lý…"
              : firstAdmin
              ? "Khởi tạo hệ thống"
              : mode === "login"
              ? "Đăng nhập"
              : "Đăng ký"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-400">
          {mode === "login" ? "Chưa có tài khoản? " : "Đã có tài khoản? "}
          <Link
            className="font-bold text-emerald-400 hover:text-emerald-300 transition"
            href={mode === "login" ? "/register" : "/login"}
          >
            {mode === "login" ? "Đăng ký" : "Đăng nhập"}
          </Link>
        </p>
        <Link
          href="/trace"
          className="mt-4 block text-center text-xs text-gray-500 hover:text-gray-300 transition"
        >
          Tra cứu QR không cần đăng nhập
        </Link>
      </div>
    </main>
  );
}

function Field({
  label,
  value,
  set,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  set: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <label className="block text-sm font-semibold text-gray-300">
      {label}
      <input
        required
        minLength={type === "password" ? 8 : 3}
        type={type}
        value={value}
        onChange={(e) => set(e.target.value)}
        placeholder={placeholder}
        className="mt-2 min-h-12 w-full rounded-xl border border-gray-700 bg-gray-950 px-4 text-white outline-none focus:border-emerald-400 transition"
      />
    </label>
  );
}
