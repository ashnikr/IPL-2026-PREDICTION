import axios from "axios";

const API_BASE =
  process.env.REACT_APP_API_URL ||
  "https://ipl-2026-prediction-pxdp.onrender.com";

const api = axios.create({ baseURL: API_BASE, timeout: 60000 });

export const healthCheck = () => api.get("/health");
export const getTeams = () => api.get("/teams");
export const getSchedule = () => api.get("/schedule");
export const getSquads = () => api.get("/squads");
export const getTeamSquad = (team) => api.get(`/squads/${team}`);
export const getNews = () => api.get("/news");
export const getTeamNews = (team) => api.get(`/news/${team}`);
export const getForm = () => api.get("/form");
export const getTeamForm = (team) => api.get(`/form/${team}`);
export const getTeamStrengths = () => api.get("/team_strengths");
export const getHeadToHead = (t1, t2) =>
  api.get("/head_to_head", { params: { team1: t1, team2: t2 } });
export const getAccuracy = () => api.get("/accuracy");

export const predictMatch = (data) => api.post("/predict_match", data);
export const predictToday = () => api.get("/predict_today");
export const runAgents = (data) => api.post("/agents", data);
export const getDream11 = (data) => api.post("/dream11", data);
export const getLivePrediction = (data) => api.post("/live", data);
export const recordResult = (data) => api.post("/result", data);

export default api;
