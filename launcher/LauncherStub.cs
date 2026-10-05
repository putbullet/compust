using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace Compust
{
    static class Program
    {
        [STAThread]
        static int Main(string[] args)
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            
            // Priority 1: Private bundled Python runtime
            string pythonw = Path.Combine(baseDir, "runtime", "pythonw.exe");
            
            // Priority 2: Developer virtual environment
            if (!File.Exists(pythonw))
            {
                pythonw = Path.Combine(baseDir, "important", ".venv", "Scripts", "pythonw.exe");
            }
            if (!File.Exists(pythonw))
            {
                pythonw = Path.Combine(baseDir, "important", ".venv", "Scripts", "python.exe");
            }
            
            // Priority 3: Fallback to PATH
            if (!File.Exists(pythonw))
            {
                pythonw = "pythonw.exe";
            }

            string script = Path.Combine(baseDir, "launcher", "launcher_core.py");
            
            // Build arguments string safely
            string arguments = "\"" + script + "\"";
            if (args != null && args.Length > 0)
            {
                foreach (string arg in args)
                {
                    arguments += " \"" + arg.Replace("\"", "\\\"") + "\"";
                }
            }

            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = pythonw,
                Arguments = arguments,
                WorkingDirectory = baseDir,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden
            };

            try
            {
                Process proc = Process.Start(psi);
                return 0;
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Unable to start Compust.\n\nDetails: " + ex.Message + "\n\nTarget runtime: " + pythonw,
                    "Compust Startup Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return 1;
            }
        }
    }
}
