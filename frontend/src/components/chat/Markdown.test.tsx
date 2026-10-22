import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { FeaturesContext } from "../../context/FeaturesContext";
import Markdown from "./Markdown";

vi.mock("../../api/study", () => ({ runCode: vi.fn() }));
import { runCode as runCodeImpl } from "../../api/study";

const runCode = runCodeImpl as unknown as Mock;

const python = "```python\nprint(sum(range(10)))\n```";

describe("Markdown code blocks", () => {
  beforeEach(() => runCode.mockReset());

  it("hides Run when the sandbox is disabled", () => {
    render(<Markdown content={python} />);
    expect(screen.queryByLabelText("Run code")).not.toBeInTheDocument();
  });

  it("runs Python and shows the output", async () => {
    runCode.mockResolvedValue({ stdout: "45\n", stderr: "", exit_code: 0, timed_out: false, duration_ms: 21 });
    render(
      <FeaturesContext.Provider value={{ google: false, sandbox: true }}>
        <Markdown content={python} />
      </FeaturesContext.Provider>
    );
    await userEvent.click(screen.getByLabelText("Run code"));
    expect(runCode).toHaveBeenCalledWith(expect.stringContaining("print(sum(range(10)))"));
    expect(await screen.findByLabelText("Program output")).toHaveTextContent("45");
    expect(screen.getByText(/Exit code 0/)).toBeInTheDocument();
  });

  it("only offers Run for Python", () => {
    render(
      <FeaturesContext.Provider value={{ google: false, sandbox: true }}>
        <Markdown content={"```bash\nrm -rf /\n```"} />
      </FeaturesContext.Provider>
    );
    expect(screen.queryByLabelText("Run code")).not.toBeInTheDocument();
  });
});
