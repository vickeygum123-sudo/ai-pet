import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

type Tone = "info" | "warning" | "success";

export function PageScaffold({
  eyebrow,
  title,
  description,
  sidebar,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  sidebar?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="page-scaffold">
      <header className="page-hero">
        <p className="page-eyebrow">{eyebrow}</p>
        <h2 className="page-title">{title}</h2>
        <p className="page-description">{description}</p>
      </header>
      <div className={`page-grid${sidebar ? "" : " page-grid-single"}`}>
        <div className="page-main-column">{children}</div>
        {sidebar ? <aside className="page-sidebar-column">{sidebar}</aside> : null}
      </div>
    </section>
  );
}

export function Panel({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h3 className="panel-title">{title}</h3>
          {description ? <p className="panel-description">{description}</p> : null}
        </div>
        {actions ? <div className="panel-actions">{actions}</div> : null}
      </div>
      <div className="panel-content">{children}</div>
    </section>
  );
}

export function Callout({
  tone = "info",
  title,
  children,
}: {
  tone?: Tone;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className={`callout callout-${tone}`}>
      <h4 className="callout-title">{title}</h4>
      <div className="callout-body">{children}</div>
    </div>
  );
}

export function Field({
  label,
  hint,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
}) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {hint ? <span className="field-hint">{hint}</span> : null}
      <input className="field-input" {...props} />
    </label>
  );
}

export function TextareaField({
  label,
  hint,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  hint?: string;
}) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {hint ? <span className="field-hint">{hint}</span> : null}
      <textarea className="field-textarea" {...props} />
    </label>
  );
}

export function StatusPill({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`status-pill status-pill-${tone}`}>{children}</span>;
}

export function DefinitionList({
  items,
}: {
  items: Array<{ label: string; value: ReactNode }>;
}) {
  return (
    <dl className="definition-list">
      {items.map((item) => (
        <div className="definition-row" key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
