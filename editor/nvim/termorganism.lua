local M = {}

local repo = "/root/TermOrganismGitFork"
local lsp_bin = repo .. "/bin/termorganism-lsp"
local presave_bin = repo .. "/bin/termorganism-pre-save"
local sidebar_bin = repo .. "/bin/termorganism-sidebar"
local preview_bin = repo .. "/bin/termorganism-fix-preview"

function M.setup_lsp()
  local ok, lspconfig = pcall(require, "lspconfig")
  if not ok then
    vim.notify("nvim-lspconfig yok", vim.log.levels.ERROR)
    return
  end

  local configs = require("lspconfig.configs")
  if not configs.termorganism then
    configs.termorganism = {
      default_config = {
        cmd = { lsp_bin },
        filetypes = { "python" },
        root_dir = function(fname)
          return lspconfig.util.find_git_ancestor(fname) or vim.fn.getcwd()
        end,
        single_file_support = true,
      },
    }
  end

  lspconfig.termorganism.setup({})
end

function M.setup_presave()
  vim.api.nvim_create_autocmd("BufWritePre", {
    pattern = "*.py",
    callback = function(args)
      local buf = args.buf
      local file = vim.api.nvim_buf_get_name(buf)
      local text = table.concat(vim.api.nvim_buf_get_lines(buf, 0, -1, false), "\n")

      local res = vim.system(
        { presave_bin, file, "--stdin", "--json", "--block-on-error" },
        { text = true, stdin = text }
      ):wait()

      if not res.stdout or res.stdout == "" then
        return
      end

      local ok, payload = pcall(vim.json.decode, res.stdout)
      if not ok then
        vim.notify("TermOrganism pre-save JSON parse failed", vim.log.levels.WARN)
        return
      end

      if payload.has_error then
        vim.notify("TermOrganism save blocked: " .. (payload.top_whisper or "error"), vim.log.levels.ERROR)
        error("TermOrganism blocked save")
      elseif payload.has_warning then
        vim.notify("TermOrganism: " .. (payload.top_whisper or "warning"), vim.log.levels.WARN)
      end
    end,
  })
end

local function open_float(title, content, ft)
  local buf = vim.api.nvim_create_buf(false, true)
  local lines = vim.split(content or "", "\n", { plain = true, trimempty = false })
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].filetype = ft or "markdown"

  local width = math.floor(vim.o.columns * 0.55)
  local height = math.floor(vim.o.lines * 0.55)

  vim.api.nvim_open_win(buf, true, {
    relative = "editor",
    row = 2,
    col = math.floor((vim.o.columns - width) / 2),
    width = width,
    height = height,
    border = "rounded",
    title = title,
    title_pos = "center",
  })
end

function M.sidebar_once()
  local file = vim.api.nvim_buf_get_name(0)
  if file == "" then
    vim.notify("Aktif dosya yok", vim.log.levels.WARN)
    return
  end

  local res = vim.system({ sidebar_bin, file, "--once" }, { text = true }):wait()
  open_float("TermOrganism Sidebar", res.stdout or "{}", "json")
end

function M.preview_fixes()
  local file = vim.api.nvim_buf_get_name(0)
  if file == "" then
    vim.notify("Aktif dosya yok", vim.log.levels.WARN)
    return
  end

  local res = vim.system({ preview_bin, file, "--json" }, { text = true }):wait()
  open_float("TermOrganism Fix Preview", res.stdout or "{}", "json")
end

function M.setup_commands()
  vim.api.nvim_create_user_command("TermOrganismSidebar", function()
    M.sidebar_once()
  end, {})

  vim.api.nvim_create_user_command("TermOrganismPreSave", function()
    local file = vim.api.nvim_buf_get_name(0)
    local text = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
    local res = vim.system(
      { presave_bin, file, "--stdin", "--json" },
      { text = true, stdin = text }
    ):wait()

    if res.stdout and res.stdout ~= "" then
      open_float("TermOrganism Pre-Save", res.stdout, "json")
    end
  end, {})

  vim.api.nvim_create_user_command("TermOrganismPreviewFixes", function()
    M.preview_fixes()
  end, {})
end

function M.setup()
  M.setup_lsp()
  M.setup_presave()
  M.setup_commands()
end

return M
