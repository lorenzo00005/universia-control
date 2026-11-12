import { Component, ErrorInfo, ReactNode } from "react";

interface State { error: Error | null }

/** Evita la pantalla en blanco: si algo falla al renderizar, muestra el error en vez de desmontar todo. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Error de la interfaz:", error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div className="center">
        <div className="card" style={{ maxWidth: 640 }}>
          <h3>Algo falló en la pantalla</h3>
          <pre className="error" style={{ whiteSpace: "pre-wrap" }}>{error.message}{"\n\n"}{error.stack?.split("\n").slice(0, 6).join("\n")}</pre>
          <button className="primary" onClick={() => location.reload()}>Recargar</button>
        </div>
      </div>
    );
  }
}
