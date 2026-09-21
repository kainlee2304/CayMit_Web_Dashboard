import axios from "axios";

const API = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL ||
        (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000"),
});

let isRefreshing = false;
let refreshSubscribers: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = [];

function subscribeTokenRefresh(resolve: (token: string) => void, reject: (err: any) => void) {
    refreshSubscribers.push({ resolve, reject });
}

function onRefreshed(token: string) {
    refreshSubscribers.forEach((cb) => cb.resolve(token));
    refreshSubscribers = [];
}

function onRefreshError(error: any) {
    refreshSubscribers.forEach((cb) => cb.reject(error));
    refreshSubscribers = [];
}

const UUID_REGEX = /^[0-9a-fA-F-]{36}$/;

API.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("caymit_access_token") || localStorage.getItem("trace_token");
        if (token && (!config.headers.Authorization || config.headers.Authorization === "Bearer ")) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        const orgId = localStorage.getItem("tammy_organization_id");
        if (orgId && UUID_REGEX.test(orgId) && !config.headers["X-Organization-ID"]) {
            config.headers["X-Organization-ID"] = orgId;
        }
    }

    if (config.headers) {
        const keysToRemove: string[] = [];
        const devHeaderLog: Record<string, string> = {};

        for (const [key, val] of Object.entries(config.headers)) {
            const strVal = String(val ?? "");
            if (/[^\x00-\x7F]/.test(strVal)) {
                if (process.env.NODE_ENV !== "production") {
                    console.warn(`[Header Sanitizer] Stripped invalid non-ASCII header '${key}': "${strVal}"`);
                }
                keysToRemove.push(key);
                continue;
            }

            if (process.env.NODE_ENV !== "production") {
                if (key.toLowerCase() === "authorization") {
                    devHeaderLog[key] = "(typeof: string, value: [REDACTED_BEARER_TOKEN])";
                } else {
                    devHeaderLog[key] = `(typeof: ${typeof val}, value: "${strVal}")`;
                }
            }
        }

        for (const key of keysToRemove) {
            delete config.headers[key];
        }

        if (process.env.NODE_ENV !== "production") {
            console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, devHeaderLog);
        }
    }

    return config;
});

API.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        if (!originalRequest) return Promise.reject(error);

        // Development logger for non-2xx API errors
        if (process.env.NODE_ENV !== "production" && error.response) {
            console.warn(`[API ${error.response.status}] ${originalRequest.method?.toUpperCase()} ${originalRequest.url}`, {
                status: error.response.status,
                data: error.response.data,
            });
        }

        // 401 Unauthorized -> Handle single-flight refresh
        if (error.response?.status === 401) {
            const isAuthEndpoint =
                originalRequest.url?.includes("/auth/login") ||
                originalRequest.url?.includes("/auth/refresh");

            if (originalRequest._retry || isAuthEndpoint) {
                return Promise.reject(error);
            }

            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    subscribeTokenRefresh(
                        (token: string) => {
                            originalRequest.headers.Authorization = `Bearer ${token}`;
                            resolve(API(originalRequest));
                        },
                        (err: any) => reject(err)
                    );
                });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            const storedRefreshToken =
                typeof window !== "undefined"
                    ? localStorage.getItem("caymit_refresh_token") || localStorage.getItem("trace_refresh_token")
                    : null;

            if (!storedRefreshToken) {
                isRefreshing = false;
                if (typeof window !== "undefined") {
                    localStorage.removeItem("caymit_access_token");
                    localStorage.removeItem("caymit_refresh_token");
                    localStorage.removeItem("trace_token");
                    if (!window.location.pathname.startsWith("/login")) {
                        window.location.href = "/login";
                    }
                }
                return Promise.reject(error);
            }

            try {
                const baseURL = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");
                const res = await axios.post(`${baseURL}/api/v1/auth/refresh`, {
                    refresh_token: storedRefreshToken
                });

                const newAccessToken = res.data.access_token;
                const newRefreshToken = res.data.refresh_token;

                if (typeof window !== "undefined") {
                    localStorage.setItem("caymit_access_token", newAccessToken);
                    localStorage.setItem("trace_token", newAccessToken);
                    if (newRefreshToken) {
                        localStorage.setItem("caymit_refresh_token", newRefreshToken);
                    }
                }

                onRefreshed(newAccessToken);
                originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
                return API(originalRequest);
            } catch (refreshErr) {
                onRefreshError(refreshErr);
                if (typeof window !== "undefined") {
                    localStorage.removeItem("caymit_access_token");
                    localStorage.removeItem("caymit_refresh_token");
                    localStorage.removeItem("trace_token");
                    if (!window.location.pathname.startsWith("/login")) {
                        window.location.href = "/login";
                    }
                }
                return Promise.reject(refreshErr);
            } finally {
                isRefreshing = false;
            }
        }

        return Promise.reject(error);
    }
);

export type Prediction = {
    id: number;
    predicted_class: string;
    confidence: number;
    all_scores: Record<string, number>;
    model_used: string;
    image_path: string | null;
    device_id: string | null;
    created_at: string;
    batch_id?: number | null;
    trace_code?: string | null;
};
export type PredictionPage = { items: Prediction[]; total: number; page: number; page_size: number; pages: number };

export type ModelInfo = {
    name: string;
    type: string;
    class_names: string[];
};

export type SensorData = {
    id: number;
    temperature: number;
    humidity: number;
    device_id: string | null;
    created_at: string;
};

export type Summary = {
    total_predictions: number;
    class_breakdown: Record<string, number>;
    latest_sensor: {
        temperature: number | null;
        humidity: number | null;
        recorded_at: string | null;
    };
};

export type TraceEvent = {
    id: number;
    block_index: number;
    stage: string;
    title: string;
    actor: string;
    location: string | null;
    details: string | null;
    event_time: string;
    previous_hash: string;
    block_hash: string;
};

export type TraceBatch = {
    trace_code: string;
    product_name: string;
    variety: string | null;
    farm_name: string;
    origin: string;
    harvest_date: string | null;
    plot_code: string | null;
    quantity: number | null;
    unit: string | null;
    status: string;
    locked: boolean;
    owner_organization: string | null;
    created_at: string;
    ledger_type: "permissioned_hash_chain";
    verified: boolean;
    broken_at_block: number | null;
    latest_hash: string | null;
    trace_url: string;
    qr_url: string;
    events: TraceEvent[];
};
export type TraceBatchPage = { items:TraceBatch[]; total:number; page:number; page_size:number; pages:number };

export type TraceRole =
    | "admin_hq"
    | "farmer"
    | "technician"
    | "packhouse_lead"
    | "qa_qc"
    | "logistics"
    | "admin"
    | "producer"
    | "processor";

export type TraceUser = {
    id: string | number;
    username: string;
    display_name: string;
    organization: string;
    organization_id?: string;
    role: TraceRole;
    roles?: string[];
    permissions?: string[];
    data_scope?: string;
    active: boolean;
    approved: boolean;
    created_at: string;
    last_login_at: string | null;
};
export type TraceAuth = { access_token:string; refresh_token?:string; token_type:"bearer"; user:TraceUser };

const authHeaders = (token?: string) => {
    const activeToken = (token && token.trim()) || (typeof window !== "undefined" ? localStorage.getItem("caymit_access_token") || localStorage.getItem("trace_token") : "");
    return activeToken ? { Authorization: `Bearer ${activeToken}` } : {};
};

// API helpers
export const getPredictions = (params?: Record<string, string | number>) =>
    API.get<Prediction[]>("/api/predict", { params }).then((r) => r.data);

export const getPredictionsPage = (params?: Record<string, string | number>) =>
    API.get<PredictionPage>("/api/predict/page", { params }).then((r) => r.data);

export const getModels = () =>
    API.get<ModelInfo[]>("/api/predict/models").then((r) => r.data);

export const getLatestSensor = () =>
    API.get<SensorData>("/api/sensors/latest").then((r) => r.data);

export const getSummary = () =>
    API.get<Summary>("/api/stats/summary").then((r) => r.data);

export const getTraceBatch = (code: string) =>
    API.get<TraceBatch>(`/api/traceability/${encodeURIComponent(code)}`).then((r) => r.data);

export const getTraceBatches = (token: string, params?:{page?:number;page_size?:number;search?:string;batch_status?:string}) =>
    API.get<TraceBatchPage>("/api/traceability/batches", {headers:authHeaders(token),params}).then((r) => r.data);

export const getTraceAuthStatus = async () => {
    try {
        return await API.get<{initialized:boolean}>("/api/traceability/auth/status").then((r) => r.data);
    } catch {
        return { initialized: true };
    }
};

export const bootstrapTraceAdmin = (payload: {username:string;password:string;display_name:string;organization:string}) =>
    API.post<TraceAuth>("/api/traceability/auth/bootstrap", payload).then((r) => r.data);

export const loginTrace = async (payload: {username:string;password:string}): Promise<TraceAuth> => {
    const res = await API.post("/api/v1/auth/login", {
        username_or_email: payload.username,
        password: payload.password
    });
    const data = res.data;
    
    if (typeof window !== "undefined") {
        localStorage.setItem("caymit_access_token", data.access_token);
        localStorage.setItem("trace_token", data.access_token);
        if (data.refresh_token) {
            localStorage.setItem("caymit_refresh_token", data.refresh_token);
        }
        if (data.organization_id) {
            localStorage.setItem("tammy_organization_id", data.organization_id);
        }
    }

    const meRes = await API.get("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${data.access_token}` }
    });
    const me = meRes.data;

    let role: TraceRole = "farmer";
    if (me.roles?.includes("admin_hq") || me.roles?.includes("admin")) role = "admin_hq";
    else if (me.roles?.includes("technician")) role = "technician";
    else if (me.roles?.includes("farmer") || me.roles?.includes("producer")) role = "farmer";
    else if (me.roles?.includes("packhouse_lead") || me.roles?.includes("processor")) role = "packhouse_lead";
    else if (me.roles?.includes("qa_qc")) role = "qa_qc";
    else if (me.roles?.includes("logistics")) role = "logistics";
    else if (me.roles?.[0]) role = me.roles[0] as TraceRole;

    const traceUser: TraceUser = {
        id: me.id,
        username: me.username,
        display_name: me.full_name || me.username,
        organization: me.active_organization?.org_name || "HTX Tam Mỹ",
        organization_id: me.active_organization?.id,
        role,
        roles: me.roles || [role],
        permissions: me.permissions || [],
        data_scope: me.data_scope || "OWN",
        active: me.is_active,
        approved: true,
        created_at: new Date().toISOString(),
        last_login_at: new Date().toISOString()
    };

    return {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        token_type: "bearer",
        user: traceUser
    };
};

export const registerTrace = (payload: {username:string;password:string;display_name:string;organization:string;role:Exclude<TraceRole,"admin"|"admin_hq">}) =>
    API.post<{message:string;user:TraceUser}>("/api/traceability/auth/register", payload).then((r) => r.data);

export const getTraceMe = async (token: string): Promise<TraceUser> => {
    const meRes = await API.get("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${token}` }
    });
    const me = meRes.data;

    let role: TraceRole = "farmer";
    if (me.roles?.includes("admin_hq") || me.roles?.includes("admin")) role = "admin_hq";
    else if (me.roles?.includes("technician")) role = "technician";
    else if (me.roles?.includes("farmer") || me.roles?.includes("producer")) role = "farmer";
    else if (me.roles?.includes("packhouse_lead") || me.roles?.includes("processor")) role = "packhouse_lead";
    else if (me.roles?.includes("qa_qc")) role = "qa_qc";
    else if (me.roles?.includes("logistics")) role = "logistics";
    else if (me.roles?.[0]) role = me.roles[0] as TraceRole;

    return {
        id: me.id,
        username: me.username,
        display_name: me.full_name || me.username,
        organization: me.active_organization?.org_name || "HTX Tam Mỹ",
        organization_id: me.active_organization?.id,
        role,
        roles: me.roles || [role],
        permissions: me.permissions || [],
        data_scope: me.data_scope || "OWN",
        active: me.is_active,
        approved: true,
        created_at: new Date().toISOString(),
        last_login_at: new Date().toISOString()
    };
};

export const createTraceBatch = (token: string, payload: {product_name:string;variety?:string;farm_name:string;origin:string;harvest_date?:string;plot_code?:string;quantity?:number;unit?:string}) =>
    API.post<TraceBatch>("/api/traceability/batches", payload, {headers:authHeaders(token)}).then((r) => r.data);

export const appendTraceEvent = (token: string, code: string, payload: {stage:string;title:string;location?:string;details?:string}) =>
    API.post<TraceBatch>(`/api/traceability/${encodeURIComponent(code)}/events`, payload, {headers:authHeaders(token)}).then((r) => r.data);

export const grantTraceBatchAccess = (token:string, code:string, username:string) =>
    API.post<{message:string;user:TraceUser}>(`/api/traceability/batches/${encodeURIComponent(code)}/access`, {username}, {headers:authHeaders(token)}).then(r=>r.data);

export const lockTraceBatch = (token:string, code:string) =>
    API.post<TraceBatch>(`/api/traceability/batches/${encodeURIComponent(code)}/lock`, null, {headers:authHeaders(token)}).then(r=>r.data);

export const getTraceUsers = (token: string) =>
    API.get<TraceUser[]>("/api/traceability/users", {headers:authHeaders(token)}).then((r) => r.data);

export const createTraceUser = (token: string, payload: {username:string;password:string;display_name:string;organization:string;role:TraceRole}) =>
    API.post<TraceUser>("/api/traceability/users", payload, {headers:authHeaders(token)}).then((r) => r.data);

export const updateTraceUserStatus = (token:string,userId:number,payload:{approved:boolean;active:boolean}) =>
    API.patch<TraceUser>(`/api/traceability/users/${userId}`,payload,{headers:authHeaders(token)}).then(r=>r.data);

export type AuditLog={id:number;user_id:number|null;action:string;resource_type:string;resource_id:string|null;details:Record<string,unknown>;ip_address:string|null;created_at:string};
export const getAuditLogs=(token:string,page=1)=>API.get<{items:AuditLog[];total:number;page:number;pages:number}>("/api/traceability/audit",{headers:authHeaders(token),params:{page}}).then(r=>r.data);

export const getDiseaseChart = (days = 7) =>
    API.get("/api/stats/chart/disease", { params: { days } }).then((r) => r.data);

export const getSensorChart = (hours = 24) =>
    API.get("/api/stats/chart/sensor", { params: { hours } }).then((r) => r.data);

export const setLight = (device_id: string, light_on: boolean) =>
    API.post("/api/devices/light", { device_id, light_on }).then((r) => r.data);

export const captureFromCamera = (model_name = "best_11") =>
    API.post("/api/stream/capture", null, { params: { model_name, device_id: "web-camera" } }).then((r) => r.data);

export const uploadPredict = async (file: File, model_name = "best_11", trace_code?: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("model_name", model_name);
    if (trace_code) form.append("trace_code", trace_code);
    const r = await API.post<Prediction>("/api/predict", form);
    return r.data;
};

export const CLASS_LABELS: Record<string, string> = {
    not_jackfruit: "Không phát hiện trái mít hoặc cây mít",
    pink_disease: "Bệnh Nấm Hồng",
    stem_cracking_gummosis: "Nứt Thân Chảy Nhựa",
    batocera_rufomaculata: "Sâu Đục Thân",
    stripe_canker: "Bệnh Sọc Vỏ",
    Binh_thuong: "✅ Bình Thường",
    Healthy: "✅ Trái Bình Thường",
    healthy: "✅ Trái Bình Thường",
    normal: "✅ Trái Bình Thường",
    "Sau_duc_trai(BactroceraSpp)": "Sâu Đục Trái",
    "ThoiTrai(Rhizopus_stolonifer)": "Thối Trái",
    fruit_borer: "Sâu Đục Trái",
    fruit_rot: "Thối Trái",
    anthracnose: "Thán Thư Trái",
};

export const CLASS_LABELS_EN: Record<string, string> = {
    not_jackfruit: "No jackfruit or tree detected",
    pink_disease: "Pink Disease (Corticium)",
    stem_cracking_gummosis: "Stem Cracking Gummosis",
    batocera_rufomaculata: "Stem Borer (Batocera)",
    stripe_canker: "Stripe Canker",
    Binh_thuong: "✅ Healthy",
    Healthy: "✅ Healthy Fruit",
    healthy: "✅ Healthy Fruit",
    normal: "✅ Healthy Fruit",
    "Sau_duc_trai(BactroceraSpp)": "Fruit Borer",
    "ThoiTrai(Rhizopus_stolonifer)": "Fruit Rot (Rhizopus)",
    fruit_borer: "Fruit Borer",
    fruit_rot: "Fruit Rot",
    anthracnose: "Anthracnose",
};

export const getClassLabel = (cls: string, lang = "vi") => {
    if (lang === "en") return CLASS_LABELS_EN[cls] || CLASS_LABELS[cls] || cls;
    return CLASS_LABELS[cls] || cls;
};

export const CLASS_COLORS: Record<string, string> = {
    not_jackfruit: "#94a3b8",
    pink_disease: "#f472b6",
    stem_cracking_gummosis: "#fb923c",
    batocera_rufomaculata: "#a78bfa",
    stripe_canker: "#34d399",
    Binh_thuong: "#4ade80",
    Healthy: "#4ade80",
    healthy: "#4ade80",
    normal: "#4ade80",
    "Sau_duc_trai(BactroceraSpp)": "#f59e0b",
    "ThoiTrai(Rhizopus_stolonifer)": "#ef4444",
    fruit_borer: "#f59e0b",
    fruit_rot: "#ef4444",
    anthracnose: "#fb7185",
};

export const MODEL_LABELS: Record<string, string> = {
    best_11: "Thân/cành - YOLOv11",
    best_26: "Thân/cành - YOLOv26",
    jackfruit_yolov26m_cls: "Trái mít - YOLOv26m-cls",
    jackfruit_efficientnet_b0: "Trái mít - EfficientNet-B0",
};

export const FALLBACK_MODELS: ModelInfo[] = [
    { name: "best_11", type: "yolo_cls", class_names: [] },
    { name: "best_26", type: "yolo_cls", class_names: [] },
    { name: "jackfruit_yolov26m_cls", type: "yolo_cls", class_names: [] },
    { name: "jackfruit_efficientnet_b0", type: "efficientnet_b0", class_names: [] },
];

const HEALTHY_CLASSES = new Set(["Binh_thuong", "Healthy", "healthy", "normal"]);

export function isHealthyClass(cls?: string | null) {
    return !!cls && HEALTHY_CLASSES.has(cls);
}

type AdviceInput = Pick<Prediction, "predicted_class">;

export function getOverallAdvice(p?: AdviceInput | null) {
    if (!p) return null;
    const label = CLASS_LABELS[p.predicted_class] || p.predicted_class;
    if (isHealthyClass(p.predicted_class)) {
        return {
            status: "Không phát hiện dấu hiệu bệnh rõ ràng",
            advice: "Tiếp tục theo dõi định kỳ, giữ vườn thông thoáng, tránh ứ đọng nước và kiểm tra thêm thân, lá, trái non.",
        };
    }
    return {
        status: `Phát hiện dấu hiệu: ${label}`,
        advice: "Nên đánh dấu vị trí phát hiện, chụp thêm ảnh ở nhiều góc, cắt bỏ phần bị hại nặng và tham khảo cán bộ nông nghiệp trước khi phun thuốc.",
    };
}

export type Treatment = {
    cause: string;
    symptoms: string;
    steps: string[];
    prevention: string[];
    severity: "low" | "medium" | "high";
};

export const DISEASE_TREATMENTS: Record<string, Treatment> = {
    pink_disease: {
        cause: "Nấm Erythricium salmonicolor gây ra, lây lan qua gió, mưa và dụng cụ cắt tỉa.",
        symptoms: "Cành bị bọc lớp nấm màu hồng cam, vỏ cây nứt, nhựa chảy ra, lá héo vàng rồi rụng.",
        severity: "high",
        steps: [
            "Cắt bỏ toàn bộ cành nhiễm bệnh, cắt sâu thêm 15–20 cm vào phần lành.",
            "Thu gom và tiêu hủy (đốt) toàn bộ tàn dư cành lá bị nhiễm.",
            "Bôi thuốc bảo vệ vết cắt bằng vôi + đồng sulfat (hỗn hợp Bordeaux) hoặc thuốc gốc đồng.",
            "Phun thuốc trừ nấm: Hexaconazole, Propiconazole hoặc Mancozeb, phun 2–3 lần cách nhau 7 ngày.",
            "Bón phân kali và canxi để tăng sức đề kháng cho cây.",
        ],
        prevention: [
            "Khử trùng dụng cụ cắt tỉa bằng cồn 70° trước và sau khi dùng.",
            "Tỉa cành tạo thông thoáng, tránh ẩm ướt kéo dài.",
            "Phun phòng Bordeaux định kỳ vào đầu và cuối mùa mưa.",
        ],
    },
    stem_cracking_gummosis: {
        cause: "Nấm Phytophthora palmivora kết hợp điều kiện đất ngập úng, thoát nước kém.",
        symptoms: "Vỏ thân nứt dọc, chảy nhựa màu trắng đục hoặc nâu vàng, phần gỗ bên trong thối đen.",
        severity: "high",
        steps: [
            "Cải thiện thoát nước ngay lập tức: đào rãnh thoát nước quanh gốc.",
            "Nạo sạch phần vỏ bệnh, cạo đến tận gỗ lành.",
            "Bôi hỗn hợp Ridomil Gold (Metalaxyl) + nước vào vết thương.",
            "Phun hoặc tưới gốc bằng Fosetyl-Al hoặc Metalaxyl pha loãng theo khuyến cáo.",
            "Bón vôi quanh gốc để nâng pH đất, hạn chế nấm Phytophthora.",
        ],
        prevention: [
            "Trồng cây trên mô đất cao hoặc luống đắp, đảm bảo thoát nước tốt.",
            "Không để nước đọng quanh gốc cây quá 4 tiếng.",
            "Phun Fosetyl-Al phòng ngừa 2 lần/năm vào đầu mùa mưa.",
        ],
    },
    batocera_rufomaculata: {
        cause: "Xén tóc Batocera rufomaculata đục vào thân/cành, sâu non đục phá bên trong.",
        symptoms: "Lỗ đục trên thân, mùn cưa và phân sâu rơi xuống gốc, cành héo đột ngột.",
        severity: "medium",
        steps: [
            "Cắt và tiêu hủy ngay cành/nhánh bị sâu nặng.",
            "Dùng dây kẽm nhỏ thọc vào lỗ đục để diệt sâu non bên trong.",
            "Bơm thuốc Chlorpyrifos hoặc Cypermethrin pha loãng vào lỗ đục, bịt miệng lỗ lại.",
            "Phun Cypermethrin lên toàn thân cây để diệt trứng và xén tóc trưởng thành.",
            "Bôi vôi + lưu huỳnh lên thân cây để ngăn xén tóc đẻ trứng.",
        ],
        prevention: [
            "Quét vôi lên thân cây 2 lần/năm (đầu và cuối mùa mưa).",
            "Bẫy đèn vào ban đêm để bắt xén tóc trưởng thành.",
            "Kiểm tra vườn định kỳ mỗi 2 tuần trong mùa khô.",
        ],
    },
    stripe_canker: {
        cause: "Nấm Phytophthora palmivora hoặc vi khuẩn, thường xuất hiện sau thương tổn cơ học.",
        symptoms: "Sọc hoặc vết loét dài theo thân vỏ cây màu nâu đen, nhựa chảy theo sọc.",
        severity: "medium",
        steps: [
            "Cạo sạch toàn bộ phần vỏ bị sọc/loét đến tận mô lành.",
            "Bôi thuốc gốc đồng (Copper hydroxide) hoặc hỗn hợp Bordeaux vào vết thương.",
            "Phun Metalaxyl + Mancozeb lên toàn bộ thân và cành.",
            "Bón phân cân đối NPK kết hợp bổ sung vi lượng Kẽm, Canxi.",
        ],
        prevention: [
            "Tránh gây thương tổn cơ học cho vỏ cây khi thu hoạch.",
            "Xử lý vết thương bằng thuốc gốc đồng ngay sau khi tỉa cành.",
            "Phun phòng nấm bệnh trước và sau mùa mưa.",
        ],
    },
    fruit_borer: {
        cause: "Sâu đục trái tấn công vào trái, thường gặp khi vườn rậm rạp hoặc trái không được bao/bảo vệ.",
        symptoms: "Trái có lỗ đục, phân sâu hoặc nhựa chảy ở vỏ; phần múi bên trong dễ thối, rụng non.",
        severity: "medium",
        steps: [
            "Thu gom và tiêu hủy trái bị hại nặng để giảm nguồn sâu.",
            "Bao trái sớm sau khi đậu trái, kiểm tra định kỳ các trái có dấu hiệu lỗ đục.",
            "Tỉa cành tạo thông thoáng và vệ sinh tàn dư quanh gốc.",
        ],
        prevention: [
            "Bao trái đúng thời điểm.",
            "Theo dõi bẫy và kiểm tra vườn 7-10 ngày/lần trong giai đoạn nuôi trái.",
            "Không để trái bệnh rơi rụng lâu trong vườn.",
        ],
    },
    fruit_rot: {
        cause: "Nấm và vi sinh vật gây thối phát triển mạnh trong điều kiện ẩm cao, trái bị xây xát hoặc thoát nước kém.",
        symptoms: "Vỏ trái xuất hiện mảng nâu đen, mềm nhũn, có thể chảy dịch và lan nhanh.",
        severity: "high",
        steps: [
            "Loại bỏ trái thối khỏi vườn, không ủ chung với phân hữu cơ chưa xử lý.",
            "Giảm ẩm quanh tán, tỉa cành thấp và cải thiện thoát nước.",
            "Có thể dùng thuốc gốc đồng hoặc thuốc nấm theo khuyến cáo địa phương khi bệnh lan rộng.",
        ],
        prevention: [
            "Tránh làm trầy xước trái khi chăm sóc và thu hoạch.",
            "Bao trái và giữ tán cây thông thoáng.",
            "Kiểm tra sau mưa kéo dài để xử lý sớm.",
        ],
    },
    anthracnose: {
        cause: "Nấm Colletotrichum spp. thường phát triển trong điều kiện ẩm, mưa nhiều và tán cây thiếu thông thoáng.",
        symptoms: "Vết đốm nâu đen lõm trên vỏ trái, có thể lan rộng và làm trái thối cục bộ.",
        severity: "medium",
        steps: [
            "Cắt tỉa cành rậm và loại bỏ trái/vật liệu nhiễm bệnh.",
            "Hạn chế tưới phun lên tán vào chiều tối.",
            "Phun thuốc nấm phù hợp theo hướng dẫn kỹ thuật nếu bệnh xuất hiện nhiều.",
        ],
        prevention: [
            "Duy trì tán thông thoáng, giảm ẩm kéo dài.",
            "Bao trái và vệ sinh vườn thường xuyên.",
            "Bón phân cân đối, tránh thừa đạm.",
        ],
    },
    Binh_thuong: {
        cause: "Không phát hiện dấu hiệu bệnh.",
        symptoms: "Cây phát triển bình thường, không có triệu chứng bất thường.",
        severity: "low",
        steps: [
            "Duy trì chế độ tưới nước và bón phân theo lịch.",
            "Tiếp tục theo dõi định kỳ để phát hiện sớm bệnh.",
        ],
        prevention: [
            "Cắt tỉa cành tạo thông thoáng.",
            "Bổ sung phân hữu cơ để tăng sức đề kháng cây.",
            "Kiểm tra và phun phòng nấm bệnh mỗi 3 tháng.",
        ],
    },
};

DISEASE_TREATMENTS.healthy = DISEASE_TREATMENTS.Binh_thuong;
DISEASE_TREATMENTS.normal = DISEASE_TREATMENTS.Binh_thuong;
DISEASE_TREATMENTS.Healthy = DISEASE_TREATMENTS.Binh_thuong;
DISEASE_TREATMENTS["Sau_duc_trai(BactroceraSpp)"] = DISEASE_TREATMENTS.fruit_borer;
DISEASE_TREATMENTS["ThoiTrai(Rhizopus_stolonifer)"] = DISEASE_TREATMENTS.fruit_rot;

// ==========================================
// Phase 5 Agricultural Core API & Types
// ==========================================

export interface GeoJSONGeometry {
    type: "Polygon" | "MultiPolygon" | "Point";
    coordinates: any;
}

export interface CropVariety {
    id: string;
    crop_code: string;
    variety_code: string;
    name: string;
    description?: string;
    scientific_name?: string;
    origin_country?: string;
    is_active: boolean;
}

export interface Crop {
    id: string;
    crop_code: string;
    name: string;
    scientific_name?: string;
    varieties?: CropVariety[];
}

export interface FarmerProfile {
    id: string;
    user_id: string;
    username: string;
    full_name: string;
    phone_number: string;
    email?: string;
    organization_id: string;
    created_at: string;
}

export interface GrowingArea {
    id: string;
    organization_id: string;
    area_code: string;
    area_name: string;
    puc_registration_code?: string;
    puc_issued_at?: string;
    puc_expires_at?: string;
    puc_status: string;
    province_code: string;
    district_code: string;
    commune_code: string;
    total_area_hectares: number;
    boundary_polygon?: GeoJSONGeometry;
    created_at: string;
}

export interface Farm {
    id: string;
    organization_id: string;
    growing_area_id: string;
    farm_code: string;
    farm_name: string;
    owner_farmer_user_id: string;
    owner_name?: string;
    address_line?: string;
    farm_area_hectares: number;
    plot_count?: number;
    created_at: string;
}

export interface TreeGroup {
    id: string;
    crop_variety_code: string;
    variety_name?: string;
    planting_year: number;
    tree_count: number;
}

export interface ClaimStatusHistory {
    id: string;
    previous_status: string;
    new_status: string;
    previous_assurance_level: string;
    new_assurance_level: string;
    transition_reason?: string;
    transitioned_by: string;
    transitioned_by_name?: string;
    occurred_at: string;
}

export interface EvidenceRecord {
    id: string;
    evidence_type: string;
    evidence_hash: string;
    captured_at: string;
    metadata_json?: Record<string, any>;
    created_at: string;
}

export interface DataClaim {
    id: string;
    organization_id: string;
    claim_type: string;
    subject_type: string;
    subject_id: string;
    value_code: string;
    value_json?: Record<string, any>;
    declared_by: string;
    declared_by_name?: string;
    declared_at: string;
    source_type: string;
    assurance_level: string;
    verification_status: string;
    verified_by?: string;
    verified_by_name?: string;
    verified_at?: string;
    verification_method?: string;
    risk_score: number;
    is_current: boolean;
    created_at: string;
    status_history?: ClaimStatusHistory[];
    evidence_records?: EvidenceRecord[];
}

export interface Plot {
    id: string;
    farm_id: string;
    farm_name?: string;
    plot_code: string;
    plot_name: string;
    boundary_polygon?: GeoJSONGeometry;
    geodesic_area_hectares?: number;
    soil_type?: string;
    irrigation_system?: string;
    current_variety_claim?: DataClaim;
    tree_groups: TreeGroup[];
    created_at: string;
}

export interface GlobalSearchResult {
    query: string;
    total_matches: number;
    farmers: Array<{ id: string; username: string; full_name: string; phone_number: string }>;
    growing_areas: Array<{ id: string; area_code: string; area_name: string; puc_status: string }>;
    farms: Array<{ id: string; farm_code: string; farm_name: string; owner_name?: string }>;
    plots: Array<{ id: string; plot_code: string; plot_name: string; farm_name?: string }>;
}

// Master Data APIs
export const getMasterCrops = (lang = "vi") =>
    API.get<Crop[]>(`/api/v1/master-data/crops?lang=${lang}`).then((r) => r.data);

export const getMasterVarieties = (cropCode = "JACKFRUIT", lang = "vi") =>
    API.get<CropVariety[]>(`/api/v1/master-data/varieties?crop_code=${cropCode}&lang=${lang}`).then((r) => r.data);

// Farmers APIs
export const getFarmers = () =>
    API.get<FarmerProfile[]>("/api/v1/farmers").then((r) => r.data);

export const getFarmerById = (id: string) =>
    API.get<FarmerProfile>(`/api/v1/farmers/${id}`).then((r) => r.data);

export const createFarmer = (data: {
    organization_id: string;
    username: string;
    full_name_vi: string;
    phone_number: string;
    email?: string;
    password?: string;
}) => API.post<FarmerProfile>("/api/v1/farmers", data).then((r) => r.data);

// Growing Areas APIs
export const getGrowingAreas = () =>
    API.get<GrowingArea[]>("/api/v1/growing-areas").then((r) => r.data);

export const getGrowingAreaById = (id: string) =>
    API.get<GrowingArea>(`/api/v1/growing-areas/${id}`).then((r) => r.data);

export const createGrowingArea = (data: {
    organization_id: string;
    area_code: string;
    area_name: string;
    puc_registration_code?: string;
    puc_issued_at?: string;
    puc_expires_at?: string;
    puc_status?: string;
    province_code: string;
    district_code: string;
    commune_code: string;
    boundary_polygon: GeoJSONGeometry;
}) => API.post<GrowingArea>("/api/v1/growing-areas", data).then((r) => r.data);

export const updateGrowingAreaStatus = (id: string, status: string, notes?: string) =>
    API.patch<GrowingArea>(`/api/v1/growing-areas/${id}/status`, { puc_status: status, notes }).then((r) => r.data);

// Farms APIs
export const getFarms = () =>
    API.get<Farm[]>("/api/v1/farms").then((r) => r.data);

export const getFarmById = (id: string) =>
    API.get<Farm>(`/api/v1/farms/${id}`).then((r) => r.data);

export const createFarm = (data: {
    organization_id: string;
    growing_area_id: string;
    farm_code: string;
    farm_name: string;
    owner_farmer_user_id: string;
    address_line?: string;
    farm_area_hectares: number;
}) => API.post<Farm>("/api/v1/farms", data).then((r) => r.data);

// Plots APIs
export const getPlots = (farmId?: string) =>
    API.get<Plot[]>("/api/v1/plots", { params: farmId ? { farm_id: farmId } : {} }).then((r) => r.data);

export const getPlotById = (id: string) =>
    API.get<Plot>(`/api/v1/plots/${id}`).then((r) => r.data);

export const createPlot = (data: {
    farm_id: string;
    plot_code: string;
    plot_name: string;
    boundary_polygon: GeoJSONGeometry;
    soil_type?: string;
    irrigation_system?: string;
    tree_groups?: Array<{
        crop_variety_code: string;
        planting_year: number;
        tree_count: number;
    }>;
}) => API.post<Plot>("/api/v1/plots", data).then((r) => r.data);

// Claims APIs
export const getClaims = (params?: { subject_id?: string; claim_type?: string; is_current?: boolean }) =>
    API.get<DataClaim[]>("/api/v1/claims", { params }).then((r) => r.data);

export const getClaimById = (id: string) =>
    API.get<DataClaim>(`/api/v1/claims/${id}`).then((r) => r.data);

export const declareClaim = (data: {
    organization_id: string;
    claim_type: string;
    subject_type: string;
    subject_id: string;
    value_code: string;
    evidence_notes?: string;
    gps_latitude?: number;
    gps_longitude?: number;
}) => API.post<DataClaim>("/api/v1/claims", data).then((r) => r.data);

export const verifyClaim = (claimId: string, data: {
    decision: "VERIFY" | "REJECT";
    verification_method?: string;
    notes?: string;
}) => API.post<DataClaim>(`/api/v1/claims/${claimId}/verify`, data).then((r) => r.data);

// Global Search API
export const globalSearch = (query: string) =>
    API.get<GlobalSearchResult>(`/api/v1/search?q=${encodeURIComponent(query)}`).then((r) => r.data);

// ==========================================
// Phase 6 Season & Farm Diary API & Types
// ==========================================

export interface YieldEstimate {
    id: string;
    estimation_method: string;
    estimated_yield_kg: number;
    confidence_level_pct: number;
    estimated_by_name?: string;
    notes?: string;
    created_at: string;
}

export interface ActivityType {
    id: string;
    activity_code: string;
    name_vi: string;
    name_en: string;
    name?: string;
    instructions_vi?: string;
    instructions_en?: string;
    instructions?: string;
    requires_material: boolean;
    requires_gps_photo: boolean;
    is_active: boolean;
}

export interface MaterialType {
    id: string;
    type_code: string;
    is_quarantine_restricted: boolean;
    is_organic_allowed: boolean;
    is_active: boolean;
}

export interface Material {
    id: string;
    organization_id: string;
    material_type_id: string;
    material_type_code?: string;
    material_code: string;
    brand_name: string;
    manufacturer?: string;
    active_ingredient?: string;
    active_ingredient_concentration?: string;
    pre_harvest_interval_days: number;
    standard_dosage_per_ha?: string;
    is_organic_certified: boolean;
    is_active: boolean;
    batches_count?: number;
    total_remaining_stock?: number;
}

export interface MaterialBatch {
    id: string;
    material_id: string;
    material_name?: string;
    material_code?: string;
    pre_harvest_interval_days?: number;
    batch_number: string;
    manufacturing_date: string;
    expiration_date: string;
    initial_quantity: number;
    remaining_quantity: number;
    unit_id: string;
    unit_code: string;
    unit_name?: string;
    storage_location?: string;
    is_active: boolean;
}

export interface MaterialUsage {
    id: string;
    activity_id: string;
    material_batch_id: string;
    material_name?: string;
    material_code?: string;
    batch_number?: string;
    quantity_applied: number;
    unit_code?: string;
    unit_name?: string;
    phi_days_applied: number;
    earliest_safe_harvest_date?: string;
    application_method?: string;
}

export interface FarmActivity {
    id: string;
    season_id: string;
    season_name?: string;
    season_code?: string;
    plot_id?: string;
    plot_name?: string;
    activity_type_id: string;
    activity_type_code?: string;
    activity_name_vi?: string;
    activity_name_en?: string;
    activity_name?: string;
    activity_code: string;
    performed_by_user_id: string;
    performed_by_name?: string;
    performed_at: string;
    gps_point?: GeoJSONGeometry;
    gps_accuracy_meters?: number;
    is_geofence_verified: boolean;
    duration_hours?: number;
    weather_condition?: string;
    notes?: string;
    verification_status: string;
    assurance_level: string;
    verified_by_user_id?: string;
    verified_by_name?: string;
    verified_at?: string;
    verification_method?: string;
    verification_notes?: string;
    created_at: string;
    updated_at: string;
    materials: MaterialUsage[];
    evidence_records?: EvidenceRecord[];
}

export interface CropSeason {
    id: string;
    plot_id: string;
    plot_name?: string;
    farm_name?: string;
    organization_id?: string;
    season_code: string;
    season_name: string;
    start_date: string;
    expected_harvest_start: string;
    expected_harvest_end: string;
    actual_harvest_end?: string;
    forecasted_yield_kg: number;
    actual_harvested_yield_kg: number;
    season_status: "DRAFT" | "ACTIVE" | "HARVESTING" | "CLOSED" | "CANCELLED";
    closed_at?: string;
    inherited_variety_code?: string;
    inherited_variety_name_vi?: string;
    inherited_variety_name_en?: string;
    inherited_variety_name?: string;
    is_variety_verified?: boolean;
    variety_assurance_level?: string;
    activities_count?: number;
    materials_used_count?: number;
    created_at: string;
    updated_at: string;
}

export interface SeasonDetail extends CropSeason {
    yield_estimates: YieldEstimate[];
    farm_activities: FarmActivity[];
    materials_summary: {
        total_applications: number;
        earliest_safe_harvest_date?: string;
        is_safe_to_harvest: boolean;
        longest_phi_material?: string;
        longest_phi_days?: number;
    };
}

// Master Activity Types API
export const getMasterActivityTypes = (lang = "vi") =>
    API.get<ActivityType[]>(`/api/v1/master-data/activity-types?lang=${lang}`).then((r) => r.data);

// Materials APIs
export const getMaterials = (materialTypeCode?: string) =>
    API.get<Material[]>("/api/v1/materials", { params: materialTypeCode ? { material_type_code: materialTypeCode } : {} }).then((r) => r.data);

export const getMaterialBatches = (materialId?: string) =>
    API.get<MaterialBatch[]>("/api/v1/materials/batches", { params: materialId ? { material_id: materialId } : {} }).then((r) => r.data);

export const createMaterialBatch = (data: {
    material_id: string;
    batch_number: string;
    manufacturing_date: string;
    expiration_date: string;
    initial_quantity: number;
    unit_id: string;
    storage_location?: string;
}) => API.post<MaterialBatch>("/api/v1/materials/batches", data).then((r) => r.data);

// Seasons APIs
export const getSeasons = (params?: { plot_id?: string; season_status?: string }) =>
    API.get<CropSeason[]>("/api/v1/seasons", { params }).then((r) => r.data);

export const getSeasonById = (id: string) =>
    API.get<SeasonDetail>(`/api/v1/seasons/${id}`).then((r) => r.data);

export const createSeason = (data: {
    plot_id: string;
    season_name: string;
    start_date: string;
    expected_harvest_start: string;
    expected_harvest_end: string;
    forecasted_yield_kg: number;
}) => API.post<CropSeason>("/api/v1/seasons", data).then((r) => r.data);

export const closeSeason = (id: string, notes?: string) =>
    API.post<CropSeason>(`/api/v1/seasons/${id}/close`, { notes }).then((r) => r.data);

// Farm Activities / Diary APIs
export const getFarmActivities = (params?: { season_id?: string; plot_id?: string; verification_status?: string }) =>
    API.get<FarmActivity[]>("/api/v1/farm-activities", { params }).then((r) => r.data);

export const getFarmActivityById = (id: string) =>
    API.get<FarmActivity>(`/api/v1/farm-activities/${id}`).then((r) => r.data);

export const createFarmActivity = (data: {
    season_id: string;
    activity_type_id: string;
    performed_at: string;
    gps_point?: GeoJSONGeometry;
    gps_accuracy_meters?: number;
    duration_hours?: number;
    weather_condition?: string;
    notes?: string;
    materials?: Array<{
        material_batch_id: string;
        quantity_applied: number;
        unit_id: string;
        application_method?: string;
    }>;
    evidence_photo_base64?: string;
}) => API.post<FarmActivity>("/api/v1/farm-activities", data).then((r) => r.data);

export const verifyFarmActivity = (id: string, data: {
    decision: "APPROVED" | "REJECTED";
    verification_method?: string;
    notes?: string;
}) => API.post<FarmActivity>(`/api/v1/farm-activities/${id}/verify`, data).then((r) => r.data);



