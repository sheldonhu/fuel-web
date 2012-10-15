module Astute
  module Network
    def self.check_network(ctx, nodes, networks)
      if nodes.length < 2
        Astute.logger.info "#{ctx.task_id}: Network checker: at least two nodes are required to check network connectivity. Do nothing."
        return false
      end
      macs = nodes.map {|n| n['mac'].gsub(":", "")}
      # TODO Everything breakes if agent not found. We have to handle that
      net_probe = MClient.new(ctx, "net_probe", macs)

      net_probe.start_frame_listeners(:iflist => ['eth0'].to_json)
      
      # Interface name is hardcoded for now. Later we expect it to be passed from Nailgun backend
      data_to_send = {'eth0' => networks.map {|n| n['vlan_id']}.join(',')}
      net_probe.send_probing_frames(:interfaces => data_to_send.to_json)

      stats = net_probe.get_probing_info
      # TODO return result like [ {'node' => 'id_of_node', 'network' => [ {'iface' => 'eth0', 'vlan' => [100,101]} } ]
      p stats
    end
  end
end
