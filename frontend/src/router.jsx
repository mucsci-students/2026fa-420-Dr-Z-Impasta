import { createBrowserRouter, Navigate } from "react-router";
import App from "./App.jsx";
import ErrorPage from "./layout/ErrorPage.jsx";
import NotFound from "./layout/NotFound.jsx";
import ConfigEditor from "./modes/editor/ConfigEditor.jsx";
import ScheduleGenerator from "./modes/generator/ScheduleGenerator.jsx";
import ScheduleViewer from "./modes/viewer/ScheduleViewer.jsx";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    errorElement: <ErrorPage />,
    children: [
      { index: true, element: <Navigate to="/editor" replace /> },
      { path: "editor", element: <ConfigEditor /> },
      { path: "generator", element: <ScheduleGenerator /> },
      { path: "viewer", element: <ScheduleViewer /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
