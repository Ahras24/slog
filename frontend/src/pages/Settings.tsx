import { useEffect, useState } from "react";
import type { ChangeEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { errorMessage } from "@/lib/errors";
import { fetchSettings, qk, updateSettings } from "@/lib/queries";
import type { StoreSettingsUpdate } from "@/lib/types";

const EMPTY: StoreSettingsUpdate = {
  store_name: "",
  phone: "",
  email: "",
  street_address: "",
  city_pincode: "",
};

const FIELDS: { field: keyof StoreSettingsUpdate; label: string; testid: string; placeholder: string }[] = [
  { field: "store_name", label: "Store Name", testid: "settings-store-name-input", placeholder: "Store name" },
  { field: "phone", label: "Phone", testid: "settings-phone-input", placeholder: "Contact phone number" },
  { field: "email", label: "Email", testid: "settings-email-input", placeholder: "Contact email" },
  { field: "street_address", label: "Street Address", testid: "settings-street-input", placeholder: "Street address" },
  { field: "city_pincode", label: "City, Pincode", testid: "settings-city-input", placeholder: "City, Pincode" },
];

export default function Settings() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({ queryKey: qk.settings, queryFn: fetchSettings });
  const [form, setForm] = useState<StoreSettingsUpdate>(EMPTY);

  useEffect(() => {
    const data = settingsQuery.data;
    if (data) {
      setForm({
        store_name: data.store_name,
        phone: data.phone,
        email: data.email,
        street_address: data.street_address,
        city_pincode: data.city_pincode,
      });
    }
  }, [settingsQuery.data]);

  const mutation = useMutation({
    mutationFn: () => updateSettings(form),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: qk.settings });
      toast.success("Store settings saved");
    },
    onError: (error) => toast.error(errorMessage(error, "Could not save settings.")),
  });

  const setField = (field: keyof StoreSettingsUpdate) => (event: ChangeEvent<HTMLInputElement>) =>
    setForm((current) => ({ ...current, [field]: event.target.value }));

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500">Store details used across the panel and on new invoices.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Store Details</CardTitle>
          <CardDescription>
            These details appear in the sidebar and on newly created invoices. Existing invoices keep the details they
            were created with.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          {FIELDS.map(({ field, label, testid, placeholder }) => (
            <div key={field} className="grid gap-2">
              <Label htmlFor={`settings-${field}`}>{label}</Label>
              <Input
                id={`settings-${field}`}
                value={form[field]}
                onChange={setField(field)}
                placeholder={placeholder}
                data-testid={testid}
              />
            </div>
          ))}
          <div className="flex justify-end">
            <Button
              onClick={() => mutation.mutate()}
              disabled={settingsQuery.isLoading || mutation.isPending || !form.store_name.trim()}
              data-testid="settings-save-button"
            >
              {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save Settings
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
