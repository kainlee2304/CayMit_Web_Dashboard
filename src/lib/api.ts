import axios from "axios";

const API = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL ||
        (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000"),
});

API.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
        const token = localStorage.getItem("caymit_access_token") || localStorage.getItem("trace_token");
        if (token && !config.headers.Authorization) config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

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

export type TraceRole = "admin" | "producer" | "processor" | "logistics";
export type TraceUser = { id:number; username:string; display_name:string; organization:string; role:TraceRole; active:boolean; approved:boolean; created_at:string; last_login_at:string|null };
export type TraceAuth = { access_token:string; token_type:"bearer"; user:TraceUser };

const authHeaders = (token: string) => ({ Authorization: `Bearer ${token}` });

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

export const getTraceAuthStatus = () =>
    API.get<{initialized:boolean}>("/api/traceability/auth/status").then((r) => r.data);

export const bootstrapTraceAdmin = (payload: {username:string;password:string;display_name:string;organization:string}) =>
    API.post<TraceAuth>("/api/traceability/auth/bootstrap", payload).then((r) => r.data);

export const loginTrace = (payload: {username:string;password:string}) =>
    API.post<TraceAuth>("/api/traceability/auth/login", payload).then((r) => r.data);

export const registerTrace = (payload: {username:string;password:string;display_name:string;organization:string;role:Exclude<TraceRole,"admin">}) =>
    API.post<{message:string;user:TraceUser}>("/api/traceability/auth/register", payload).then((r) => r.data);

export const getTraceMe = (token: string) =>
    API.get<TraceUser>("/api/traceability/auth/me", {headers:authHeaders(token)}).then((r) => r.data);

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

