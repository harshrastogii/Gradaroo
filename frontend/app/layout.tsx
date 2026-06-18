export const metadata = {
  title: "Australian Resume Converter",
  description: "Convert your resume to the Australian standard format.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
