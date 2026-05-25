import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

vi.mock("./api", () => ({
  getSettings: vi.fn(),
  updateLLM: vi.fn(),
  updateEmbedding: vi.fn(),
  updateWhatsApp: vi.fn(),
  updateTelegram: vi.fn(),
  updateBot: vi.fn(),
}));

import { getSettings, updateLLM, updateEmbedding, updateWhatsApp, updateTelegram, updateBot } from "./api";
import { SettingsPage } from "./SettingsPage";
import type { TenantConfigResponse } from "./types";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <MantineProvider>
        <Notifications />
        <QueryClientProvider client={qc}>
          <MemoryRouter>{children}</MemoryRouter>
        </QueryClientProvider>
      </MantineProvider>
    );
  };
}

const CONFIG: TenantConfigResponse = {
  llm_provider: "openai",
  llm_model: "gpt-4o-mini",
  llm_api_key_masked: "sk-****1234",
  llm_max_tokens: 1024,
  llm_temperature: 0.3,
  embedding_provider: "openai",
  embedding_model: "text-embedding-3-large",
  embedding_api_key_masked: "",
  embedding_dimensions: 1536,
  whatsapp_phone_number_id: "123456",
  whatsapp_access_token_masked: "EAA****",
  whatsapp_verify_token_masked: "vt****",
  telegram_bot_token_masked: "bot****",
  telegram_webhook_secret_masked: "ws****",
  bot_name: "FD Bot",
  bot_welcome_message: "Hello there!",
  bot_language: "en",
};

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loader while loading", () => {
    vi.mocked(getSettings).mockReturnValue(new Promise(() => {}));
    const { container } = render(<SettingsPage />, { wrapper: createWrapper() });
    expect(container.querySelector(".mantine-Loader-root")).toBeTruthy();
  });

  it("shows error alert on failure", async () => {
    vi.mocked(getSettings).mockRejectedValue(new Error("fail"));
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Could not load settings.")).toBeInTheDocument();
    });
  });

  it("renders page title and description", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Settings")).toBeInTheDocument();
      expect(screen.getByText(/configure your llm provider/i)).toBeInTheDocument();
    });
  });

  it("renders all accordion sections", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("LLM Configuration")).toBeInTheDocument();
      expect(screen.getByText("Embedding Configuration")).toBeInTheDocument();
      expect(screen.getByText("WhatsApp Cloud API")).toBeInTheDocument();
      expect(screen.getByText("Telegram Bot")).toBeInTheDocument();
      expect(screen.getByText("Bot Personality")).toBeInTheDocument();
    });
  });

  it("shows LLM form fields in default open accordion", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Save LLM config")).toBeInTheDocument();
    });
  });

  it("shows embedding section when opened", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("Embedding Configuration")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Embedding Configuration"));
    await waitFor(() => {
      expect(screen.getByText("Save embedding config")).toBeInTheDocument();
    });
  });

  it("shows WhatsApp section when opened", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("WhatsApp Cloud API")).toBeInTheDocument());

    fireEvent.click(screen.getByText("WhatsApp Cloud API"));
    await waitFor(() => {
      expect(screen.getByText("Save WhatsApp config")).toBeInTheDocument();
    });
  });

  it("shows Telegram section when opened", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("Telegram Bot")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Telegram Bot"));
    await waitFor(() => {
      expect(screen.getByText("Save Telegram config")).toBeInTheDocument();
    });
  });

  it("shows Bot section when opened", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("Bot Personality")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Bot Personality"));
    await waitFor(() => {
      expect(screen.getByText("Save bot config")).toBeInTheDocument();
    });
  });

  it("submits LLM form", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    vi.mocked(updateLLM).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("Save LLM config")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Save LLM config"));
    await waitFor(() => {
      expect(updateLLM).toHaveBeenCalled();
    });
  });

  it("submits Embedding form", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    vi.mocked(updateEmbedding).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("Embedding Configuration")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Embedding Configuration"));
    await waitFor(() => expect(screen.getByText("Save embedding config")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Save embedding config"));
    await waitFor(() => {
      expect(updateEmbedding).toHaveBeenCalled();
    });
  });

  it("submits WhatsApp form", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    vi.mocked(updateWhatsApp).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("WhatsApp Cloud API")).toBeInTheDocument());

    fireEvent.click(screen.getByText("WhatsApp Cloud API"));
    await waitFor(() => expect(screen.getByText("Save WhatsApp config")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Save WhatsApp config"));
    await waitFor(() => expect(updateWhatsApp).toHaveBeenCalled());
  });

  it("submits Telegram form", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    vi.mocked(updateTelegram).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("Telegram Bot")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Telegram Bot"));
    await waitFor(() => expect(screen.getByText("Save Telegram config")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Save Telegram config"));
    await waitFor(() => expect(updateTelegram).toHaveBeenCalled());
  });

  it("shows error notification when mutation fails", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    vi.mocked(updateLLM).mockRejectedValue(new Error("fail"));
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("Save LLM config")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Save LLM config"));
    await waitFor(() => expect(updateLLM).toHaveBeenCalled());
  });

  it("submits Bot form", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    vi.mocked(updateBot).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("Bot Personality")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Bot Personality"));
    await waitFor(() => expect(screen.getByText("Save bot config")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Save bot config"));
    await waitFor(() => expect(updateBot).toHaveBeenCalled());
  });

  it("submits LLM form with filled model field", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    vi.mocked(updateLLM).mockResolvedValue(CONFIG);
    const { container } = render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("Save LLM config")).toBeInTheDocument());

    const llmPanel = container.querySelector("[data-active='true'] .mantine-Accordion-panel");
    const modelInput = llmPanel?.querySelector("input[data-path='model']") ?? screen.getAllByLabelText("Model")[0];
    fireEvent.change(modelInput, { target: { value: "gpt-4o" } });
    fireEvent.click(screen.getByText("Save LLM config"));

    await waitFor(() => {
      expect(updateLLM).toHaveBeenCalledWith(expect.objectContaining({ model: "gpt-4o" }), expect.anything());
    });
  });

  it("submits WhatsApp form with filled phone field", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    vi.mocked(updateWhatsApp).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("WhatsApp Cloud API")).toBeInTheDocument());

    fireEvent.click(screen.getByText("WhatsApp Cloud API"));
    await waitFor(() => expect(screen.getByText("Save WhatsApp config")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText("Phone Number ID"), { target: { value: "9999" } });
    fireEvent.click(screen.getByText("Save WhatsApp config"));

    await waitFor(() => {
      expect(updateWhatsApp).toHaveBeenCalledWith(expect.objectContaining({ phone_number_id: "9999" }), expect.anything());
    });
  });

  it("submits Bot form with filled name field", async () => {
    vi.mocked(getSettings).mockResolvedValue(CONFIG);
    vi.mocked(updateBot).mockResolvedValue(CONFIG);
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("Bot Personality")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Bot Personality"));
    await waitFor(() => expect(screen.getByText("Save bot config")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText("Bot Name"), { target: { value: "NewBot" } });
    fireEvent.click(screen.getByText("Save bot config"));

    await waitFor(() => {
      expect(updateBot).toHaveBeenCalledWith(expect.objectContaining({ name: "NewBot" }), expect.anything());
    });
  });

  it("renders with null whatsapp/telegram config", async () => {
    vi.mocked(getSettings).mockResolvedValue({
      ...CONFIG,
      whatsapp_phone_number_id: null,
      whatsapp_access_token_masked: null,
      whatsapp_verify_token_masked: null,
      telegram_bot_token_masked: null,
      telegram_webhook_secret_masked: null,
    });
    render(<SettingsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("Settings")).toBeInTheDocument());
  });
});
