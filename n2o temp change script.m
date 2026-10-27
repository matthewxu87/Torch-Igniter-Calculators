% INPUTS
mdot = 0.01;           % Total N2O mass flow rate [kg/s]
Qdot_in = 500;         % Heat-transfer rate into mixture [W]
Lv = 3.76e5;           % Latent heat of vaporization [J/kg]
cp_v = 900;            % Vapor specific heat [J/(kg*K)]
                       % Example placeholder; replace with a value
                       % appropriate for your N2O pressure and temperature.

% SWEEP VAPOR QUALITY FROM 90% TO 100%
quality = 0.90:0.01:1.00;   % Vapor mass fraction
n = length(quality);

deltaT = zeros(1,n);        % Vapor temperature change [K]
frac_evap = zeros(1,n);     % Fraction of initial liquid evaporated
Qdot_evap_all = zeros(1,n); % Heat rate needed to evaporate all liquid [W]

% ENERGY BALANCE
for i = 1:n

    x = quality(i);

    % Initial liquid mass flow rate
    mdot_liquid = mdot * (1 - x);

    % Heat rate required to evaporate all remaining liquid
    Qdot_evap_all(i) = mdot_liquid * Lv;

    % Determine fraction of initial liquid evaporated
    if mdot_liquid > 0
        frac_evap(i) = min(Qdot_in / Qdot_evap_all(i), 1);
    else
        frac_evap(i) = 1;  % No liquid initially present
    end

    % Heat remaining after evaporation
    Qdot_superheat = Qdot_in - Qdot_evap_all(i);

    % Equilibrium model:
    % Temperature rises only after all liquid evaporates
    if Qdot_superheat > 0
        deltaT(i) = Qdot_superheat / (mdot * cp_v);
    else
        deltaT(i) = 0;
    end

end

% DISPLAY RESULTS
results = table(quality(:)*100, ...
                Qdot_evap_all(:), ...
                frac_evap(:)*100, ...
                deltaT(:), ...
    'VariableNames', {'Quality_percent', ...
                      'Qdot_to_evaporate_W', ...
                      'Liquid_evaporated_percent', ...
                      'Vapor_deltaT_K'});

disp(results);

% PLOT
figure;
plot(quality*100, deltaT, '-o', 'LineWidth', 1.8, ...
     'MarkerSize', 6);

grid on;
xlabel('Initial Vapor Quality (%)');
ylabel('Estimated Vapor Temperature Change, \DeltaT (K)');
title('N_2O Vapor Temperature Change vs. Initial Quality');
xlim([90 100]);
xticks(90:1:100);
