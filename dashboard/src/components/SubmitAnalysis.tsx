import { useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface Props {
  onSubmit: (url: string, method: string) => void;
}

export function SubmitAnalysis({ onSubmit }: Props) {
  const [url, setUrl] = useState("");
  const [method, setMethod] = useState("GET");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    onSubmit(url.trim(), method);
    setUrl("");
  };

  return (
    <Card className="glass border-primary/20">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Submit Endpoint for Analysis</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Select value={method} onValueChange={setMethod}>
            <SelectTrigger className="w-24 shrink-0 font-mono text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {["GET", "POST", "PUT", "DELETE", "PATCH"].map((m) => (
                <SelectItem key={m} value={m} className="font-mono text-xs">{m}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="/api/v1/endpoint"
            className="flex-1 font-mono text-xs"
          />
          <Button type="submit" size="sm" disabled={!url.trim()} className="gap-1.5">
            <Send className="h-3.5 w-3.5" />
            Analyze
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
